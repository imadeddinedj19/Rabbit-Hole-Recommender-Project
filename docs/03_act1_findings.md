# Act 1 Findings: The Model Doesn't Beat Popularity (Yet)

**Status:** Phase 2 paused at step 2.4. Test users not touched. **Team decision needed** before step 2.5.

Every number here comes from validation users only and is reproduced by:

```
python src/model.py time          # step 2.1
python src/model.py tune          # step 2.4 (20 Optuna trials, ~2 min)
python scripts/act1_diagnostics.py
```

---

## What was done

- **Step 2.1, timing.** One fit at the slowest corner of the search space (100 factors, 50 epochs) takes **12.7 s** on the 1 M training rows, and time grows linearly with rows (1.2 s at 100k). Twenty tuning trials take about 2 minutes, well inside the 15–30 min budget. *We have room to grow the training set if we want.*
- **Step 2.4, tuning.** Optuna, 20 trials, lowest validation RMSE. Winner: `n_factors=20, lr_all=0.00427, reg_all=0.0446, n_epochs=35` (`results/act1_best_params.json`, all trials in `results/act1_tuning.csv`). Every trial lands between 0.517 and 0.554 RMSE, so the setting barely matters.
- `src/model.py` was checked against Surprise's own `predict` (identical to 0.0) and the metrics against a hand-computed example.

## The problem

The plan's "done when" for Act 1 is: *the model clearly beats popularity on Precision@10 and nDCG@10.* It doesn't:

| Validation, liked = watch ratio ≥ 2.0 | RMSE | Precision@10 | nDCG@10 |
| --- | --- | --- | --- |
| SVD (matrix factorization) | **0.518** | 0.674 | 0.678 |
| SVD, item bias only (same list for everyone) | 0.533 | 0.674 | 0.678 |
| Popularity (damped average watch ratio) | 0.534 | 0.668 | 0.677 |
| Random | – | 0.039 | 0.041 |

SVD predicts individual watch ratios better (lower RMSE), but its top 10 is the same as a non-personal list. The whole jump over random comes from the **item bias** `b_i`, the "everyone watches this one a lot" term.

## Why: two effects, both measured

**1. Duration bias.** Watch ratio = time watched ÷ video length, so short clips score high just by looping.

- Rank correlation between a video's length and its average watch ratio: **−0.987**.
- The model's top 10s have a median length of **3.3 s** (catalogue: 9.6 s).
- Across all 300 validation users, the top 10s contain only **14 distinct videos**.

The industry name is **duration bias**. Kuaishou, who published KuaiRec, have a paper on it: *Deconfounding Duration Bias in Watch-time Prediction* (D2Q, KDD 2022).

**2. Item effects dominate taste.** The video alone explains **30%** of watch-ratio variance in the small matrix. The user alone explains **5%**. Removing duration bias doesn't change this:

- **D2Q-style target** (percentile of a view within its video-length group; liked = top 20% for that length): recommended videos are now a normal length (median 20 s), but SVD still ties popularity (Precision@10 0.594 vs 0.600). Still only 13 distinct videos.
- **It isn't our sampling setup either.** Giving validation users 10% or 50% of their own catalogue labels in training doesn't help: SVD still ties popularity. A more flexible model (less regularization) is *worse*.

**But there is personal signal.** Redefine "liked" as *"watched at least 0.5 more than this video's usual ratio"*, i.e. liked it more than other people did:

| Validation, liked = 0.5 above the video's usual | Precision@10 | nDCG@10 |
| --- | --- | --- |
| SVD (full score) | **0.358** | **0.375** |
| Popularity (damped) | 0.339 | 0.337 |
| SVD, user-specific part only (`b_u + p_u·q_i`) | 0.163 | 0.165 |
| Random | 0.083 | 0.088 |

The user-specific part alone is 2× random, and full SVD beats popularity by about 6% (Precision@10) and 11% (nDCG@10). The gain is real, but modest.

## Why this matters beyond Act 1

Act 2 assumes the feed **narrows over time** as the user's profile drifts. If the item bias dominates the ranking, the profile barely moves the top 10, so the feed may be narrow **from round 1** and stay flat. That's a different (and arguably bigger) story: watch-time optimization doesn't trap each user in *their* niche, it gives **everyone the same short clips**. The usual term for this is **homogenization**, and it's a known side effect of **popularity bias**.

## Options

| Option | What changes | For | Against |
| --- | --- | --- | --- |
| **A. Keep the metric, reframe the story** | Act 1 reports the tie honestly; duration bias and homogenization become the headline | Most honest. Uses the data as it is. A genuinely interesting finding | Act 1 no longer "proves the model works". Act 2's drifting-feed dynamic may not appear |
| **B. Duration-debiased target (D2Q)** | Target = percentile within video-length group | Removes the short-clip artifact with a published, nameable fix | On its own, SVD still ties popularity |
| **C. "Liked more than usual" relevance** | Precision/nDCG graded on lift over the video's usual ratio | SVD beats popularity. Measures personalization directly | Less intuitive definition, has to be explained. Gain is modest |
| **D. Tune for ranking, not RMSE** | Optuna maximizes validation nDCG@10 | Small change, matches what Acts 2–3 use | Section 4 of the diagnostics suggests little upside |

**Recommendation:** decide on Act 2 first, because that's where the story lives. A quick pilot of the fold-in simulation (step 3.1) on the current model would show whether the feed narrows over rounds or is flat from the start. Then:

- If it **narrows**: go with **C** (+ **B** if the short clips look silly in the examples). Act 1 shows a modest but real personalization gain, and the plan holds.
- If it's **flat**: go with **A**. The story becomes "the watch-time recommender gives everyone the same short clips", and Act 3's re-ranker is about restoring variety across the whole platform.
