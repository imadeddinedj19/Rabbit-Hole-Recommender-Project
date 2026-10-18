# Rabbit Hole Recommender: Project Spec

Spec for building the project with Claude Code. It combines the team proposal and the data and compute plan.

## Goal

Build a simplified TikTok-style short-video recommender on KuaiRec. Show that optimizing only for watch time narrows what users see (the "rabbit hole"). Then find the cheapest way, in lost watch time, to restore diversity.

**Research question:** What happens when a recommender optimizes only for watch time, and what does it cost to make it healthier?

## Data: KuaiRec (downsampled)

- Source: https://kuairec.com/ (files: `big_matrix.csv`, `small_matrix.csv`, `item_categories.csv`)
- Never commit data. Put `data/` in `.gitignore` and write `scripts/download_data.py` to fetch it.
- Load only `user_id`, `video_id`, `watch_ratio`, using `int32` / `float32`.

### Downsampling (target: about 1M training rows)

1. Keep only the 3,327 videos that appear in `small_matrix.csv`.
2. Sample about 2,000 users from `big_matrix.csv` (out of 7,176). Adjust the count until training is about 1M rows.
3. Sample about 500 users from `small_matrix.csv` (out of 1,411) as the test set.
4. Sample whole users, not random rows, so each user's history stays intact.
5. Use a fixed seed (`random_state=42`). Save `train.parquet` and `test.parquet` to `data/processed/`.
6. Check representativeness by plotting the sample against the full data (watch ratio histogram and category mix).

## Model design

### Variables

- **Target (dependent) variable:** `watch_ratio`, capped at 3 to 5. Set the final cap after plotting the distribution.
- **Inputs (independent variables):** `user_id`, `video_id`.
- **Not model inputs:** video categories and tags. Use them only for the diversity metric and the re-ranker.
- **Task:** regression. Apply the relevance threshold only during evaluation.

### Cutoffs

| Cutoff | Value |
| --- | --- |
| Outlier cap | 3 to 5 (confirm on data) |
| Relevance threshold ("liked") | watch_ratio of about 2.0 or higher |
| K (list length) | 10 |
| Simulation rounds | 20 to 30 |
| Diversity constraint (optional) | 4 or more categories in the top 10 |

### Evaluation

- **Train/test split:** sampled big matrix for training, sampled small matrix for testing. No cross-validation, because the small matrix is the holdout.
- **Metrics:** RMSE, Precision@10, nDCG@10.
- **Baseline:** recommend the most popular videos.
- **Diversity metric:** unique categories in the top 10. Intra-list diversity (ILD) is optional.

## Pipeline

1. **Act 1, model.** Fit SVD (`surprise`) on the training set.
   - Tune `n_factors` (20 to 100), `lr_all` (0.002 to 0.01), `reg_all` (0.02 to 0.1), and `n_epochs` (20 to 50).
   - Use 15 to 20 combinations (random search or Optuna), with no cross-validation.
   - Compute test scores with NumPy from the learned factors, not the `surprise` per-pair loop.
2. **Act 2, rabbit hole simulation.**
   - Start a simulated user from one video. Each round, recommend the top 10 and the user "watches" the top pick.
   - Update only that user's vector (fold-in), keeping the video factors fixed. Never retrain the full model.
   - Log unique categories per round and plot diversity over rounds.
3. **Act 3, diversity re-ranker and optimization.**
   - Apply MMR re-ranking to the stored predictions. Tune the diversity weight λ (0 to 1) and the candidate pool size N (20 to 200).
   - Run about 100 Optuna trials with two objectives: maximize predicted watch time and maximize diversity.
   - Plot the optimization history and the Pareto frontier. Highlight three points: max engagement, balanced, and max diversity.

## Expected compute

| Step | Time |
| --- | --- |
| Load and sample | Under 1 min |
| Popularity baseline | Seconds |
| Hyperparameter tuning | 10 to 20 min |
| Final SVD fit | 1 to 2 min |
| Predict and evaluate | Under 1 min |
| Act 2 simulation | Under 1 min |
| Act 3 optimization | 2 to 5 min |
| **Total** | **About 15 to 30 min** |

Before the real runs, time one fit on 100k rows to calibrate these estimates.

## Deliverables (charts)

- Model accuracy vs. popularity baseline (table)
- Diversity over simulation rounds (line chart)
- Optuna optimization history
- Pareto frontier (watch time vs. diversity)
- Sample vs. full data representativeness check

## Suggested repo layout

```
data/              # gitignored
scripts/download_data.py
src/sample.py      # downsampling
src/model.py       # SVD, tuning, evaluation
src/simulate.py    # Act 2 fold-in simulation
src/rerank.py      # MMR + Optuna
notebooks/         # charts for slides
```
