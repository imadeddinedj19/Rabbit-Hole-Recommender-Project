"""Downsample KuaiRec into train / validation / test files.

Usage (from the repo root, after scripts/download_data.py):
    python src/sample.py
    python src/sample.py --train-rows 500000     # smaller, for a quick test

What it does (see docs/01_project_plan.md, Phase 1):
    1. Pick evaluation users from the small matrix and split them into
       validation and test groups (spec fix #2).
    2. Build the training set from the big matrix: the evaluation users'
       history first (spec fix #1), then other random users until about
       --train-rows rows. Whole users are sampled, never single rows.
    3. Remove any (user, video) pair from train that also appears in
       validation or test, so the model never sees the answers (no leakage).
    4. Save train.parquet, val.parquet, test.parquet in data/processed/.

Why training keeps ALL videos (spec fix #3): the small matrix is almost
full, so nearly every time an evaluation user watched a small-matrix video
in the big matrix, that pair is also a test pair and step 3 removes it.
Their taste can only be learned from the OTHER videos they watched. The
small-matrix videos themselves are learned from the other training users.
Recommendations and grading still use only the small-matrix videos.

The watch ratio is NOT capped here. The cap is a modelling choice, applied
in src/model.py once we have looked at the distribution.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

COLUMNS = ["user_id", "video_id", "watch_ratio"]
DTYPES = {"user_id": "int32", "video_id": "int32", "watch_ratio": "float32"}


def find_csv(name):
    """Find a KuaiRec file inside data/raw/, whatever the zip's folder name is."""
    matches = sorted(RAW_DIR.rglob(name))
    if not matches:
        raise FileNotFoundError(
            f"{name} not found in {RAW_DIR}. Run `python scripts/download_data.py` first."
        )
    return matches[0]


def load_matrix(path):
    """Load the three columns we need, using compact number types to save memory."""
    df = pd.read_csv(path, usecols=COLUMNS, dtype=DTYPES)

    # Drop broken rows (e.g. a video length of 0 gives an infinite ratio).
    n_before = len(df)
    df = df[np.isfinite(df["watch_ratio"])]

    # A user can watch the same video more than once. Keep one row per
    # (user, video) pair with the average watch ratio, so every pair counts once.
    df = df.groupby(["user_id", "video_id"], as_index=False, sort=False)["watch_ratio"].mean()
    df["watch_ratio"] = df["watch_ratio"].astype("float32")

    print(f"  {path.name}: {n_before:,} rows -> {len(df):,} unique (user, video) pairs")
    return df


def pick_users(user_ids, n, rng, label):
    """Randomly pick n users (or all of them, with a warning, if there are fewer)."""
    if n > len(user_ids):
        print(f"  Warning: asked for {n} {label} users, only {len(user_ids)} available.")
        n = len(user_ids)
    return rng.choice(user_ids, size=n, replace=False)


def build_train(big, eval_users, target_rows, rng):
    """Evaluation users' history + other random whole users up to ~target_rows."""
    is_eval = big["user_id"].isin(eval_users)
    train = big[is_eval]

    # The other users are the only source for learning the small-matrix
    # videos, so they always get at least half of the row budget.
    extra_budget = max(target_rows - len(train), target_rows // 2)
    if len(train) > target_rows // 2:
        print(
            f"  Warning: evaluation users alone give {len(train):,} rows. Training will be "
            f"~{len(train) + extra_budget:,} rows. Lower --n-test / --n-val to shrink it."
        )

    # Shuffle the other users, then add them one by one (in bulk, with a
    # running total) until the budget is used.
    rows_per_user = big.loc[~is_eval, "user_id"].value_counts()
    shuffled = rows_per_user.sample(frac=1, random_state=rng.integers(1 << 31))
    extra_users = shuffled.index[shuffled.cumsum() <= extra_budget]

    return pd.concat([train, big[big["user_id"].isin(extra_users)]], ignore_index=True)


def remove_overlap(train, held_out):
    """Drop training rows whose (user, video) pair is in validation or test."""
    key = ["user_id", "video_id"]
    merged = train.merge(held_out[key], on=key, how="left", indicator=True)
    clean = merged[merged["_merge"] == "left_only"].drop(columns="_merge")
    print(f"  Removed {len(train) - len(clean):,} overlapping (user, video) pairs from train.")
    return clean.reset_index(drop=True)


def check(train, val, test):
    """The 'done when' checks from the plan. Stops the script if one fails."""
    key = ["user_id", "video_id"]
    train_users = set(train["user_id"])
    assert set(val["user_id"]) <= train_users, "Some validation users have no training history."
    assert set(test["user_id"]) <= train_users, "Some test users have no training history."
    assert not set(val["user_id"]) & set(test["user_id"]), "Validation and test users overlap."
    for name, held_out in [("validation", val), ("test", test)]:
        overlap = train[key].merge(held_out[key], on=key)
        assert overlap.empty, f"{len(overlap)} (user, video) pairs are in both train and {name}."


def summarize(name, df):
    q = df["watch_ratio"].quantile([0.5, 0.9, 0.99]).round(2).tolist()
    print(
        f"  {name:<6} {len(df):>10,} rows | {df['user_id'].nunique():>5,} users | "
        f"{df['video_id'].nunique():>5,} videos | watch ratio p50/p90/p99 = {q}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--train-rows", type=int, default=1_000_000, help="target training rows")
    parser.add_argument("--n-test", type=int, default=500, help="test users (small matrix)")
    parser.add_argument("--n-val", type=int, default=300, help="validation users (small matrix)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    print("Loading data...")
    small = load_matrix(find_csv("small_matrix.csv"))
    big = load_matrix(find_csv("big_matrix.csv"))

    # 1. Evaluation users must have a history in the big matrix, or the model
    #    cannot learn their taste.
    candidates = np.intersect1d(small["user_id"].unique(), big["user_id"].unique())
    print(f"  Small-matrix users with a big-matrix history: {len(candidates):,}")
    eval_users = pick_users(candidates, args.n_test + args.n_val, rng, "evaluation")
    test_users, val_users = eval_users[: args.n_test], eval_users[args.n_test :]

    test = small[small["user_id"].isin(test_users)].reset_index(drop=True)
    val = small[small["user_id"].isin(val_users)].reset_index(drop=True)

    # 2 + 3. Training set, then remove leaked pairs.
    print("Building training set...")
    train = build_train(big, eval_users, args.train_rows, rng)
    train = remove_overlap(train, pd.concat([val, test]))

    check(train, val, test)

    # The model can only rank small-matrix videos it has seen in training.
    small_videos = small["video_id"].unique()
    coverage = np.isin(small_videos, train["video_id"].unique()).mean()
    print(f"  Small-matrix videos present in train: {coverage:.1%}")
    if coverage < 0.99:
        print("  Warning: some videos have no training data. Raise --train-rows.")

    # The full big matrix is shown for the representativeness check:
    # the training sample should look like it.
    print("\nSummary:")
    summarize("full", big)
    summarize("train", train)
    summarize("val", val)
    summarize("test", test)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in [("train", train), ("val", val), ("test", test)]:
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
    print(f"\nSaved train/val/test.parquet to {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
