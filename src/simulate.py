"""Act 2: simulated user and the rabbit hole (plan step 3.1).

Usage (from the repo root, after `python src/model.py fit`):
    python src/simulate.py                 # 100 starting videos, 30 rounds
    python src/simulate.py --starts 20     # quicker

What it does:
    A simulated user starts from one video. Each round:
      1. Score every catalogue video with the user's current taste profile.
      2. Drop videos already watched.
      3. Record the top 10 and how many categories it covers.
      4. The user watches the #1 video, "liking" it (watch ratio 2.0).
      5. Re-compute the user's profile from everything watched so far
         (fold-in), with every video's profile kept frozen.
    Repeated from many starting videos spread across categories.

Fold-in: find the user bias b_u and vector p_u that best explain the
watched videos' ratings, given the fixed video profiles (mu, b_i, q_i).
It's a ridge regression. The penalty is reg_all x (videos watched), which
is the penalty Surprise's training applies to a real user with that many
ratings, so the simulated user is regularized like a real one.

Outputs: results/act2_rounds.csv (one row per start and round),
results/act2_summary.json, results/figures/02_diversity_over_rounds.png.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from categories import load_categories
from model import PROC_DIR, RESULTS_DIR, Factors, SEED

ROUNDS = 30
LIST_LEN = 10
LIKED_RATIO = 2.0      # the simulated user "likes" each video it watches
RANDOM_TOP10 = 7.6     # categories in a random top 10 (notebooks/01_data.ipynb)


class Catalogue:
    """The small-matrix videos the recommender picks from, with frozen profiles."""

    def __init__(self, factors, video_ids, categories):
        self.mu = factors.mu
        self.ids = np.asarray(video_ids)
        self.bi, self.Q = factors._lookup(factors._v, self.ids, factors.bi, factors.Q)
        self.cat = categories.set_index("video_id")["category_id"].reindex(self.ids).to_numpy()

    def fold_in(self, watched, ratings, reg):
        """Ridge regression for (b_u, p_u) given the watched videos' indices."""
        X = np.column_stack([np.ones(len(watched)), self.Q[watched]])
        y = np.asarray(ratings) - self.mu - self.bi[watched]
        A = X.T @ X + reg * len(watched) * np.eye(X.shape[1])
        w = np.linalg.solve(A, X.T @ y)
        return w[0], w[1:]

    def scores(self, b_u, p_u):
        return self.mu + b_u + self.bi + self.Q @ p_u


def simulate(cat, start, reg, rounds=ROUNDS):
    """One simulated user from one starting video. Returns one dict per round."""
    watched = [start]
    log = []
    for r in range(1, rounds + 1):
        b_u, p_u = cat.fold_in(watched, [LIKED_RATIO] * len(watched), reg)
        s = cat.scores(b_u, p_u)
        s[watched] = -np.inf
        top = np.argsort(-s, kind="stable")[:LIST_LEN]
        log.append({
            "round": r,
            "unique_categories": len(np.unique(cat.cat[top])),
            "same_category_as_start": float(np.mean(cat.cat[top] == cat.cat[start])),
            "top10": cat.ids[top].tolist(),
        })
        watched.append(int(top[0]))
    return log


def pick_starts(cat, n, rng):
    """n starting videos spread across categories: round-robin over categories."""
    by_cat = [rng.permutation(np.flatnonzero(cat.cat == c)).tolist() for c in rng.permutation(np.unique(cat.cat))]
    starts = []
    while len(starts) < n and any(by_cat):
        for videos in by_cat:
            if videos and len(starts) < n:
                starts.append(videos.pop())
    return np.array(starts)


def overlap(a, b):
    """Share of videos two top-10 lists have in common (0 = none, 1 = identical)."""
    return len(set(a) & set(b)) / LIST_LEN


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--starts", type=int, default=100, help="starting videos")
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    args = parser.parse_args()

    factors = Factors.load(PROC_DIR / "svd_factors.npz")
    reg = json.loads((RESULTS_DIR / "act1_best_params.json").read_text())["reg_all"]
    catalogue_ids = np.sort(pd.read_parquet(PROC_DIR / "val.parquet", columns=["video_id"])["video_id"].unique())
    cat = Catalogue(factors, catalogue_ids, load_categories())

    rng = np.random.default_rng(SEED)
    starts = pick_starts(cat, args.starts, rng)
    rows = []
    for i, start in enumerate(starts):
        for row in simulate(cat, start, reg, args.rounds):
            rows.append({"start": i, "start_video": int(cat.ids[start]), **row})
    df = pd.DataFrame(rows)

    # What a brand-new user with no history sees: the item part only (mu + b_i).
    anonymous = cat.ids[np.argsort(-(cat.mu + cat.bi), kind="stable")[:LIST_LEN]].tolist()
    df["overlap_with_anonymous_feed"] = df["top10"].map(lambda t: overlap(t, anonymous))

    # How similar are different users' feeds in the same round? Average over
    # all pairs of starting videos: 1 = everyone sees the same list.
    lists = df.pivot(index="start", columns="round", values="top10")
    pair_overlap = {}
    for r in lists.columns:
        col = lists[r].tolist()
        pairs = [overlap(col[a], col[b]) for a in range(len(col)) for b in range(a + 1, len(col))]
        pair_overlap[r] = float(np.mean(pairs))

    per_round = df.groupby("round").agg(
        unique_categories=("unique_categories", "mean"),
        p10=("unique_categories", lambda x: x.quantile(0.1)),
        p90=("unique_categories", lambda x: x.quantile(0.9)),
        same_category_as_start=("same_category_as_start", "mean"),
        overlap_with_anonymous_feed=("overlap_with_anonymous_feed", "mean"),
    )
    per_round["overlap_between_users"] = pd.Series(pair_overlap)

    first, last = per_round.iloc[0], per_round.iloc[-1]
    drop = first["unique_categories"] - last["unique_categories"]
    if drop >= 2 and last["overlap_between_users"] < 0.5:
        verdict = "narrows"
    elif abs(drop) < 1 and last["overlap_between_users"] >= 0.5:
        verdict = "flat"
    else:
        verdict = "mixed"

    summary = {
        "starts": int(len(starts)), "rounds": int(args.rounds),
        "unique_categories_round_1": round(float(first["unique_categories"]), 2),
        f"unique_categories_round_{args.rounds}": round(float(last["unique_categories"]), 2),
        "drop": round(float(drop), 2),
        "overlap_between_users_round_1": round(float(first["overlap_between_users"]), 3),
        f"overlap_between_users_round_{args.rounds}": round(float(last["overlap_between_users"]), 3),
        "overlap_with_anonymous_feed_round_1": round(float(first["overlap_with_anonymous_feed"]), 3),
        f"overlap_with_anonymous_feed_round_{args.rounds}": round(float(last["overlap_with_anonymous_feed"]), 3),
        "distinct_videos_in_all_feeds": int(len(set(v for t in df["top10"] for v in t))),
        "random_top10_categories": RANDOM_TOP10,
        "verdict": verdict,
        "rule": "narrows: drop >= 2 categories and users' feeds overlap < 50% at the end; "
                "flat: |drop| < 1 and overlap >= 50%; otherwise mixed",
    }

    df.drop(columns="top10").to_csv(RESULTS_DIR / "act2_rounds.csv", index=False)
    (RESULTS_DIR / "act2_summary.json").write_text(json.dumps(summary, indent=2))
    print(per_round.round(3).iloc[[0, 1, 2, 4, 9, 19, -1]].to_string())
    print(json.dumps(summary, indent=2))
    plot(per_round, summary)


def plot(per_round, summary):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    x = per_round.index
    ax.fill_between(x, per_round["p10"], per_round["p90"], color="#2a78d6", alpha=0.15, lw=0,
                    label="Middle 80% of simulated users")
    ax.plot(x, per_round["unique_categories"], color="#2a78d6", lw=2, label="Average simulated user")
    for y, text in [(10, "Maximum (10 different categories)"),
                    (RANDOM_TOP10, f"Random top 10 (≈{RANDOM_TOP10})")]:
        ax.axhline(y, color="#8a8984", lw=1.2, ls=":")
        ax.text(x.max(), y + 0.15, text, ha="right", va="bottom", fontsize=9, color="#52514e")
    ax.set(xlabel="Round (videos watched so far)", ylabel="Categories in the top 10",
           ylim=(0, 10.8), xlim=(1, x.max()),
           title="Act 2 pilot: how varied is the feed as the user keeps watching?")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color="#ebeae6", lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower left")
    out = RESULTS_DIR / "figures" / "02_diversity_over_rounds.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"saved {out.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
