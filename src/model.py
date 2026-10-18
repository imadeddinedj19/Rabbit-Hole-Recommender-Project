"""Act 1: matrix factorization (SVD) vs. popularity, tuning and evaluation.

Usage (from the repo root, after src/sample.py):
    python src/model.py time        # step 2.1: time one fit, check the budget
    python src/model.py tune        # step 2.4: Optuna on the VALIDATION users
    python src/model.py fit         # final fit only, saves the factors (no test users)
    python src/model.py evaluate    # step 2.5: final fit, graded ONCE on test

What it does (see docs/01_project_plan.md, Phase 2):
    - Target: watch_ratio capped at CAP (decisions log). Inputs: user_id, video_id.
    - Model: Surprise SVD. Scores are computed in NumPy from the learned
      factors (mu + b_u + b_i + p_u . q_i), not with Surprise's per-pair loop.
    - Ranking: for each evaluation user, every small-matrix video they have a
      label for is scored, and the top K is graded against their real watch
      ratios. The small matrix is ~99.6% full, so almost nothing is left out.
    - Baselines: the same top K for everyone, by a damped average watch ratio
      or by view count.

Outputs:
    results/act1_timing.json, act1_tuning.csv, act1_best_params.json,
    act1_metrics.csv, and data/processed/svd_factors.npz (for Acts 2 and 3).
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"

CAP = 4.0          # outlier cap on the target (decisions log, proposed)
THRESHOLD = 2.0    # watch ratio at or above which a video counts as "liked"
K = 10             # list length
SEED = 42
DAMPING = 10       # popularity baseline: views of "global average" added to each video

SEARCH_SPACE = {   # spec ranges
    "n_factors": (20, 100),
    "lr_all": (0.002, 0.01),
    "reg_all": (0.02, 0.1),
    "n_epochs": (20, 50),
}


def load_splits():
    return tuple(pd.read_parquet(PROC_DIR / f"{n}.parquet") for n in ("train", "val", "test"))


# ---------------------------------------------------------------- the model

def fit_svd(train, params, seed=SEED):
    """Fit Surprise SVD on the capped watch ratio."""
    data = Dataset.load_from_df(
        train[["user_id", "video_id"]].assign(r=train["watch_ratio"].clip(upper=CAP)),
        Reader(rating_scale=(0, CAP)),
    )
    algo = SVD(**params, random_state=seed)
    algo.fit(data.build_full_trainset())
    return algo


class Factors:
    """The learned profiles as NumPy arrays, indexed by raw user/video ids.

    Users or videos the model never saw get a zero vector and zero bias, so
    they fall back to the global mean (what Surprise does too).
    """

    def __init__(self, mu, user_ids, bu, P, video_ids, bi, Q):
        self.mu = float(mu)
        self.user_ids, self.bu, self.P = np.asarray(user_ids), bu, P
        self.video_ids, self.bi, self.Q = np.asarray(video_ids), bi, Q
        self._u = pd.Series(np.arange(len(self.user_ids)), index=self.user_ids)
        self._v = pd.Series(np.arange(len(self.video_ids)), index=self.video_ids)

    @classmethod
    def from_surprise(cls, algo):
        ts = algo.trainset
        user_ids = [ts.to_raw_uid(i) for i in range(ts.n_users)]
        video_ids = [ts.to_raw_iid(i) for i in range(ts.n_items)]
        return cls(ts.global_mean, user_ids, algo.bu, algo.pu, video_ids, algo.bi, algo.qi)

    def _lookup(self, index, ids, bias, vectors):
        pos = index.reindex(ids).to_numpy()
        known = ~np.isnan(pos)
        b = np.zeros(len(ids))
        V = np.zeros((len(ids), vectors.shape[1]))
        b[known] = bias[pos[known].astype(int)]
        V[known] = vectors[pos[known].astype(int)]
        return b, V

    def score(self, users, videos):
        """users x videos matrix of predicted (capped-scale) watch ratios."""
        bu, P = self._lookup(self._u, users, self.bu, self.P)
        bi, Q = self._lookup(self._v, videos, self.bi, self.Q)
        return np.clip(self.mu + bu[:, None] + bi[None, :] + P @ Q.T, 0, CAP)

    def save(self, path):
        np.savez(path, mu=self.mu, user_ids=self.user_ids, bu=self.bu, P=self.P,
                 video_ids=self.video_ids, bi=self.bi, Q=self.Q)

    @classmethod
    def load(cls, path):
        f = np.load(path)
        return cls(f["mu"], f["user_ids"], f["bu"], f["P"], f["video_ids"], f["bi"], f["Q"])


# -------------------------------------------------------------- baselines

def popularity_scores(train, videos):
    """Two "same list for everyone" baselines, one score per video.

    - damped mean: average capped watch ratio, pulled toward the global
      average by DAMPING imaginary views, so a video watched once at 4.0
      doesn't top the chart. Also used as the baseline's RMSE prediction.
    - view count: how many training users watched it.
    """
    wr = train["watch_ratio"].clip(upper=CAP)
    mu = wr.mean()
    g = wr.groupby(train["video_id"]).agg(["sum", "count"])
    damped = ((g["sum"] + DAMPING * mu) / (g["count"] + DAMPING)).reindex(videos, fill_value=mu)
    views = g["count"].reindex(videos, fill_value=0).astype(float)
    return damped.to_numpy(), views.to_numpy()


# ------------------------------------------------------------- evaluation

def truth_matrix(held_out):
    """users x videos matrix of real watch ratios (NaN where there is no label)."""
    m = held_out.pivot(index="user_id", columns="video_id", values="watch_ratio")
    return m.index.to_numpy(), m.columns.to_numpy(), m.to_numpy(dtype=float)


def rmse(pred, truth):
    has = ~np.isnan(truth)
    return float(np.sqrt(np.mean((pred[has] - np.minimum(truth[has], CAP)) ** 2)))


def ranking_metrics(scores, truth, exclude=None, k=None, threshold=None):
    """Mean Precision@k and nDCG@k over users (defaults: K and THRESHOLD).

    Only videos with a label are ranked (scores of the rest set to -inf), and
    `exclude` (a boolean mask, e.g. videos seen in training) removes more.
    Relevance is binary: real watch ratio >= threshold (uncapped).
    """
    # Defaults are read at call time, so changing K or THRESHOLD takes effect.
    k = K if k is None else k
    threshold = THRESHOLD if threshold is None else threshold
    scores = np.where(np.isnan(truth), -np.inf, scores)
    if exclude is not None:
        scores = np.where(exclude, -np.inf, scores)
    top = np.argsort(-scores, axis=1, kind="stable")[:, :k]
    rel = np.nan_to_num(np.take_along_axis(truth, top, axis=1)) >= threshold

    discounts = 1 / np.log2(np.arange(2, k + 2))
    dcg = (rel * discounts).sum(axis=1)
    n_rel = np.minimum((np.nan_to_num(truth) >= threshold).sum(axis=1), k)
    idcg = np.array([discounts[:n].sum() for n in n_rel])
    ndcg = np.divide(dcg, idcg, out=np.zeros_like(dcg), where=idcg > 0)
    return float(rel.mean(axis=1).mean()), float(ndcg.mean())


def seen_in_train(train, users, videos):
    """Boolean users x videos mask of pairs the user already watched in training."""
    seen = train[train["user_id"].isin(users) & train["video_id"].isin(videos)]
    mask = np.zeros((len(users), len(videos)), dtype=bool)
    u = pd.Series(np.arange(len(users)), index=users)
    v = pd.Series(np.arange(len(videos)), index=videos)
    mask[u[seen["user_id"]].to_numpy(), v[seen["video_id"]].to_numpy()] = True
    return mask


def evaluate(models, train, held_out):
    """One row of RMSE / Precision@K / nDCG@K per model on a held-out set.

    `models` maps a name to a function (users, videos) -> (ranking scores,
    predicted watch ratios), both users x videos. They are the same matrix
    for SVD. The predictions are None for a model that only ranks.
    """
    users, videos, truth = truth_matrix(held_out)
    exclude = seen_in_train(train, users, videos)
    rows = []
    for name, model in models.items():
        scores, preds = model(users, videos)
        p, n = ranking_metrics(scores, truth, exclude)
        rows.append({"model": name, "RMSE": rmse(preds, truth) if preds is not None else np.nan,
                     f"Precision@{K}": p, f"nDCG@{K}": n})
    return pd.DataFrame(rows).set_index("model")


def svd_model(factors):
    def model(users, videos):
        s = factors.score(users, videos)
        return s, s
    return model


def baseline_models(train):
    """Same list for everyone. "Most viewed" only ranks: a view count is not
    a watch ratio, so it has no RMSE."""
    def damped(users, videos):
        s = np.tile(popularity_scores(train, videos)[0], (len(users), 1))
        return s, s

    def views(users, videos):
        return np.tile(popularity_scores(train, videos)[1], (len(users), 1)), None

    def global_mean(users, videos):
        # No ranking signal at all: every video scores the same. RMSE floor only.
        s = np.full((len(users), len(videos)), train["watch_ratio"].clip(upper=CAP).mean())
        return s, s

    return {"Popularity (damped avg watch ratio)": damped,
            "Popularity (most viewed)": views,
            "Global mean (RMSE reference)": global_mean}


# --------------------------------------------------------------- commands

def cmd_time(train, val, test):
    """Step 2.1: one fit on 100k rows, then one on the full training set."""
    params = {"n_factors": 100, "n_epochs": 50, "lr_all": 0.005, "reg_all": 0.02}  # slowest corner
    users = train["user_id"].drop_duplicates().sample(frac=1, random_state=SEED)
    sizes = train.groupby("user_id").size().reindex(users).cumsum()
    small = train[train["user_id"].isin(sizes.index[sizes <= 100_000])]

    out = {"params": params}
    for name, df in [("100k", small), ("full", train)]:
        t0 = time.perf_counter()
        fit_svd(df, params)
        out[f"fit_seconds_{name}"] = round(time.perf_counter() - t0, 1)
        out[f"rows_{name}"] = len(df)
        print(f"  {name:>4}: {len(df):>9,} rows -> {out[f'fit_seconds_{name}']} s")
    out["tuning_20_trials_upper_bound_min"] = round(20 * out["fit_seconds_full"] / 60, 1)
    print(f"  20 tuning trials at this (slowest) setting: <= "
          f"{out['tuning_20_trials_upper_bound_min']} min")
    (RESULTS_DIR / "act1_timing.json").write_text(json.dumps(out, indent=2))


def cmd_tune(train, val, test, n_trials):
    """Step 2.4: Optuna, scored on the validation users only (spec fix #2)."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    rows = []

    def objective(trial):
        params = {
            "n_factors": trial.suggest_int("n_factors", *SEARCH_SPACE["n_factors"]),
            "lr_all": trial.suggest_float("lr_all", *SEARCH_SPACE["lr_all"], log=True),
            "reg_all": trial.suggest_float("reg_all", *SEARCH_SPACE["reg_all"], log=True),
            "n_epochs": trial.suggest_int("n_epochs", *SEARCH_SPACE["n_epochs"]),
        }
        t0 = time.perf_counter()
        f = Factors.from_surprise(fit_svd(train, params))
        m = evaluate({"svd": svd_model(f)}, train, val).loc["svd"]
        rows.append({"trial": trial.number, **params, "val_RMSE": m["RMSE"],
                     f"val_Precision@{K}": m[f"Precision@{K}"], f"val_nDCG@{K}": m[f"nDCG@{K}"],
                     "seconds": round(time.perf_counter() - t0, 1)})
        print(f"  trial {trial.number:>2}: RMSE {m['RMSE']:.4f} | nDCG@{K} {m[f'nDCG@{K}']:.4f} "
              f"| {params}")
        return m["RMSE"]

    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=n_trials)

    table = pd.DataFrame(rows).sort_values("val_RMSE")
    table.to_csv(RESULTS_DIR / "act1_tuning.csv", index=False)
    best = {k: (int(v) if k in ("n_factors", "n_epochs") else round(float(v), 5))
            for k, v in study.best_params.items()}
    (RESULTS_DIR / "act1_best_params.json").write_text(json.dumps(best, indent=2))
    print(f"\nBest (lowest validation RMSE): {best}")
    print(table.head().to_string(index=False))


def cmd_fit(train, val, test):
    """Final model with the best params, saved for Acts 2 and 3. Doesn't use test users."""
    params = json.loads((RESULTS_DIR / "act1_best_params.json").read_text())
    print(f"Final fit with {params}")
    factors = Factors.from_surprise(fit_svd(train, params))
    factors.save(PROC_DIR / "svd_factors.npz")
    print(f"Saved {(PROC_DIR / 'svd_factors.npz').relative_to(ROOT)}")
    return factors


def cmd_evaluate(train, val, test):
    """Step 2.5: final model with the best params, graded once on the test users."""
    factors = cmd_fit(train, val, test)

    models = {"SVD (matrix factorization)": svd_model(factors), **baseline_models(train)}
    tables = []
    for name, held_out in [("validation", val), ("test", test)]:
        t = evaluate(models, train, held_out)
        t.insert(0, "users", name)
        tables.append(t)
    metrics = pd.concat(tables)
    metrics.to_csv(RESULTS_DIR / "act1_metrics.csv")
    print(metrics.round(4).to_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", choices=["time", "tune", "fit", "evaluate"])
    parser.add_argument("--trials", type=int, default=20, help="Optuna trials for `tune`")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    splits = load_splits()
    if args.command == "time":
        cmd_time(*splits)
    elif args.command == "tune":
        cmd_tune(*splits, n_trials=args.trials)
    elif args.command == "fit":
        cmd_fit(*splits)
    else:
        cmd_evaluate(*splits)


if __name__ == "__main__":
    main()
