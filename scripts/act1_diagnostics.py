"""Act 1 diagnostics: why SVD does not beat popularity (validation users only).

Usage (from the repo root, after `python src/model.py tune`):
    python scripts/act1_diagnostics.py

Reproduces every number in docs/03_act1_findings.md. Never touches test users.
    1. SVD vs. its own item bias vs. popularity vs. random.
    2. Duration bias: video length vs. watch ratio, and what gets recommended.
    3. Duration-debiased target (percentile within a video-length group, D2Q-style).
    4. Validation users given some of their own catalogue labels in training.
    5. "Liked" = watched more than this video's usual ratio (personal lift).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import model as M  # noqa: E402
from model import (CAP, Factors, baseline_models, evaluate, fit_svd, load_splits,  # noqa: E402
                   popularity_scores, ranking_metrics, svd_model, truth_matrix)
from sample import find_csv  # noqa: E402


def item_bias_only(factors):
    """The model's score for an unknown user: mu + b_i. Same list for everyone."""
    def model(users, videos):
        s = np.tile(factors.score(np.array([-1]), videos)[0], (len(users), 1))
        return s, s
    return model


def random_model(seed=0):
    rng = np.random.default_rng(seed)
    return lambda users, videos: (rng.random((len(users), len(videos))), None)


def compare(factors, train, held_out):
    return evaluate({"SVD": svd_model(factors), "SVD item bias only": item_bias_only(factors),
                     **baseline_models(train), "Random": random_model()}, train, held_out)


def top10(factors, held_out):
    users, videos, truth = truth_matrix(held_out)
    s = np.where(np.isnan(truth), -np.inf, factors.score(users, videos))
    return videos[np.argsort(-s, axis=1)[:, :10]]


def main():
    train, val, _ = load_splits()
    params = json.loads((ROOT / "results" / "act1_best_params.json").read_text())
    factors = Factors.from_surprise(fit_svd(train, params))

    print("== 1. SVD vs. baselines (validation, liked = watch ratio >= 2.0)")
    print(compare(factors, train, val).round(4).to_string())

    print("\n== 2. Duration bias")
    cols = ["video_id", "video_duration", "watch_ratio"]
    small = pd.read_csv(find_csv("small_matrix.csv"), usecols=cols)
    small = small[np.isfinite(small["watch_ratio"])]
    dur = pd.concat([small, pd.read_csv(find_csv("big_matrix.csv"), usecols=cols[:2])]) \
        .groupby("video_id")["video_duration"].median() / 1000
    video_mean = small.groupby("video_id")["watch_ratio"].mean()
    print(f"Spearman(video length, video's mean watch ratio): "
          f"{dur.reindex(video_mean.index).corr(video_mean, method='spearman'):.3f}")
    small["user_id"] = pd.read_csv(find_csv("small_matrix.csv"), usecols=["user_id"])["user_id"]
    w = small["watch_ratio"].clip(upper=CAP)
    for key, label in [("video_id", "the video"), ("user_id", "the user")]:
        r2 = 1 - ((w - w.groupby(small[key]).transform("mean")) ** 2).sum() / ((w - w.mean()) ** 2).sum()
        print(f"Share of watch-ratio variance explained by {label} alone: {r2:.1%}")
    rec = top10(factors, val)
    print(f"Distinct videos across all validation users' top 10s: {len(np.unique(rec))}")
    print(f"Median length (s): recommended {np.median(dur.reindex(rec.ravel())):.1f} "
          f"| catalogue {dur.reindex(small['video_id'].unique()).median():.1f}")

    print("\n== 3. Duration-debiased target: percentile of the view within its video-length decile")
    edges = np.quantile(dur.reindex(train["video_id"].unique()).dropna(), np.linspace(0, 1, 11))
    edges[0], edges[-1] = -np.inf, np.inf
    group = lambda df: pd.cut(df["video_id"].map(dur), edges, labels=False).to_numpy()  # noqa: E731
    g_train = group(train)
    ref = {g: np.sort(train["watch_ratio"].to_numpy()[g_train == g]) for g in range(10)}

    def percentile(df):
        g, wr, out = group(df), df["watch_ratio"].to_numpy(), np.empty(len(df))
        for k in range(10):
            out[g == k] = np.searchsorted(ref[k], wr[g == k], side="right") / len(ref[k])
        return out

    train_p, val_p = train.assign(watch_ratio=percentile(train)), val.assign(watch_ratio=percentile(val))
    old = M.CAP, M.THRESHOLD
    M.CAP, M.THRESHOLD = 1.0, 0.8   # target on a 0-1 scale; liked = top 20% for that length
    f_p = Factors.from_surprise(fit_svd(train_p, params))
    print(compare(f_p, train_p, val_p).round(4).to_string())
    rec = top10(f_p, val_p)
    print(f"Distinct videos in top 10s: {len(np.unique(rec))} | "
          f"median recommended length: {np.median(dur.reindex(rec.ravel())):.1f} s")
    M.CAP, M.THRESHOLD = old

    print("\n== 4. Validation users see part of their own catalogue labels in training")
    rng = np.random.default_rng(42)
    for frac in [0.1, 0.5]:
        seen = rng.random(len(val)) < frac
        tr = pd.concat([train, val[seen]], ignore_index=True)
        f_h = Factors.from_surprise(fit_svd(tr, params))
        res = evaluate({"SVD": svd_model(f_h), "SVD item bias only": item_bias_only(f_h),
                        "Popularity (damped)": baseline_models(tr)["Popularity (damped avg watch ratio)"]},
                       tr, val[~seen])
        print(f"-- {frac:.0%} of labels seen"); print(res.round(4).to_string())

    print("\n== 5. Liked = watched at least 0.5 more than this video's usual ratio")
    users, videos, truth = truth_matrix(val)
    usual = popularity_scores(train, videos)[0]
    lift = np.minimum(truth, CAP) - usual[None, :]
    full = factors.score(users, videos)
    personal = full - factors.score(np.array([-1]), videos)[0][None, :]
    print(f"({np.nanmean(lift >= 0.5):.1%} of validation pairs)")
    rows = {name: ranking_metrics(s, lift, threshold=0.5) for name, s in [
        ("SVD personal part (b_u + p_u.q_i)", personal), ("SVD full score", full),
        ("Popularity (damped)", np.tile(usual, (len(users), 1))),
        ("Random", np.random.default_rng(0).random(full.shape))]}
    print(pd.DataFrame(rows, index=["Precision@10", "nDCG@10"]).T.round(4).to_string())


if __name__ == "__main__":
    main()
