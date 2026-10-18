# Act 1 Findings: The Model Doesn't Beat Popularity (Yet)

**Status:** decided. The Act 2 pilot showed a flat feed, so we chose **option A** (keep the metric, report the tie honestly, change the story). Step 2.5 is done: final test results are [at the end of this document](#final-test-results-step-25). The pilot is in [`04_act2_pilot.md`](04_act2_pilot.md).

---

## The short version

- **What we found:** our model recommends almost exactly the same videos as the simple "show everyone the most popular videos" approach. It isn't better at picking what a user will like.
- **What it means:** the plan says Act 1 is done only when the model *clearly* beats popularity. It doesn't yet, and Acts 2 and 3 are built on the model.
- **Why it happens:** two reasons. (1) Very short videos get high watch ratios just because they loop, so the model pushes the same handful of short clips to everyone. (2) In this data, *which video it is* matters much more than *who is watching*.
- **What we should do:** run a quick test of the Act 2 simulation first, then pick one of the options at the end of this document. The choice changes the story of the project, so it's a team call.

---

## What went fine

**Speed.** One model training run takes about **13 seconds** with the slowest settings. The spec expected minutes. The whole tuning step takes about 2 minutes, well inside the 15–30 minute budget. We have time to spare, for example to use more training data.

**Tuning.** We tried 20 different model settings (with Optuna) and kept the one with the lowest prediction error on the validation users. All 20 scored almost the same (prediction error between 0.517 and 0.554, see below for what that means). So the exact setting doesn't matter much. Saved in `results/act1_best_params.json`.

**Correctness.** The code's scores match the Surprise library's own predictions exactly, and the metric code gives the right answers on a small example worked out by hand.

---

## Finding 1: the model ties with popularity

**What we found.** On the validation users:

| Approach | Prediction error (RMSE) | Liked videos in the top 10 (Precision@10) | Ranking quality (nDCG@10) |
| --- | --- | --- | --- |
| Our model (SVD) | **0.52** | 0.67 → **6.7 of 10** | 0.68 |
| Popularity (same list for everyone) | 0.53 | 0.67 → **6.7 of 10** | 0.68 |
| Our model without its personal part | 0.53 | 0.67 → **6.7 of 10** | 0.68 |
| Random videos | – | 0.04 → **0.4 of 10** | 0.04 |

**How to read it:**

- **Liked videos in the top 10 (Precision@10)** goes from 0 to 1, higher is better. 0.67 means that out of the 10 videos we'd show, about 6.7 were "liked" (watched at least twice). Random picks get 0.4 of 10. So both the model and popularity are far better than random, but **they're equal to each other**.
- **Ranking quality (nDCG@10)** also goes from 0 to 1, higher is better. It's like Precision@10, but also rewards putting the liked videos first. Same story: tie.
- **Prediction error (RMSE)** is how far off the predicted watch ratio is, on average. Lower is better. 0.52 means a typical prediction is off by about half a video. For comparison, guessing the average for every video gives 0.63. The model is a bit better than popularity here (0.52 vs 0.53), so it does learn *something* about individual users. That just isn't enough to change which 10 videos end up on top.

**What it means.** The bottom line is row 3. If we remove everything personal from the model, the top 10 stays the same. All the benefit comes from knowing which videos are watched a lot *by everyone*. That isn't personalization, it's popularity.

---

## Finding 2: short videos win because they loop

**What we found.** The shorter a video, the higher its average watch ratio, almost without exception.

- Correlation between video length and average watch ratio: **−0.99**. Correlation goes from −1 to 1. 0 means no link, and anything beyond −0.7 counts as strong. −0.99 is almost perfect: length alone nearly decides the watch ratio.
- The videos the model recommends are **3.3 seconds** long on average (middle value). The typical video in the catalogue is 9.6 seconds.
- Across all 300 validation users, the recommendation lists contain only **14 different videos** in total. Everyone gets nearly the same list.

**What it means.** Watch ratio = time watched ÷ video length. A 3-second clip that plays on loop while you read the comments scores 3.0, "watched three times", even if you didn't care about it. So a model that maximizes watch ratio learns "recommend tiny clips". The industry name for this is **duration bias**. Kuaishou, the company that published our dataset, wrote a research paper on exactly this problem (*D2Q*, KDD 2022).

---

## Finding 3: the video matters much more than the viewer

**What we found.**

- Knowing only *which video* it is explains **30%** of the differences between views.
- Knowing only *who is watching* explains **5%**.

(Read "30%" as: if you only knew the video, you could already account for about a third of why one view is higher than another.)

**What it means.** Some videos are simply better for nearly everyone, and those win the top 10 for every user. Personal taste only reshuffles the order further down the list.

**We checked that this isn't caused by something we did:**

- **Fixing duration bias doesn't change it.** We tried Kuaishou's fix: compare each view only with videos of similar length, and count a video as "liked" if the view is in the top 20% for that length. The recommended videos became normal-length (20 seconds), but the model still tied popularity (about 5.9 vs 6.0 liked videos out of 10; random gets 1.7 of 10).
- **It isn't our data split.** Our test users have no training history on the test videos (see the Phase 1 notebook). So we gave them 10% and then 50% of their own test-video history during training. Still a tie.

---

## Finding 4: there *is* a personal signal, just a small one

**What we found.** We changed the definition of "liked" from "watched at least twice" to **"watched noticeably more than other people watched this same video"** (at least 0.5 above that video's usual watch ratio). This asks: *did this user like it more than others did?*

| Approach | Liked videos in the top 10 | Ranking quality (nDCG@10) |
| --- | --- | --- |
| Our model (SVD) | **3.6 of 10** | **0.37** |
| Popularity | 3.4 of 10 | 0.34 |
| Only the personal part of our model | 1.6 of 10 | 0.16 |
| Random | 0.8 of 10 | 0.09 |

**How to read it.** The numbers are lower than in Finding 1 because this task is harder: a popular video is no longer an automatic hit, since it has to beat its *own* usual score. Don't compare these numbers with Finding 1. Compare the rows with each other:

- The **personal part alone** finds 2× more liked videos than random. So the model really did learn individual taste.
- The **full model beats popularity**: 3.6 vs 3.4 liked videos per list, and 0.37 vs 0.34 ranking quality (+11%). In everyday terms: roughly **one extra liked video for every five users**. Real, but modest.

---

## Why this matters for Act 2

Act 2's story is: *the feed narrows step by step, because each video you watch pushes the next recommendations further toward the same topic.* That only works if the user's history changes the top 10.

Finding 1 suggests it barely does. So the feed may be **narrow from the very first round and stay flat**. That would be a different story, arguably a stronger one: watch-time optimization doesn't trap each user in *their own* niche, it gives **everyone the same short clips**. The usual term for this is **homogenization** (everyone's feed looks the same).

We don't know yet which it is. That's why the first step below is a quick test.

---

## What we should do

| Option | In plain words | Good | Bad |
| --- | --- | --- | --- |
| **A. Keep everything, change the story** | Report the tie honestly. Make "everyone gets the same short clips" the main finding | Most honest. A genuinely interesting result | Act 1 no longer shows "the model works". Act 2's step-by-step narrowing may not appear |
| **B. Fix duration bias** | Compare each view only with videos of similar length | Removes the "tiny clips win" problem with a published method | On its own, the model still ties popularity |
| **C. New definition of "liked"** | "Liked" = watched more than other people watched this video | The model beats popularity. Measures personal taste directly | Harder to explain, and the gain is small |
| **D. Tune for ranking** | Pick model settings by ranking quality instead of prediction error | Small change | Our tests suggest it won't help much |

**Recommendation:** first run a quick test of the Act 2 simulation on the current model, because Act 2 is where the story lives. Then:

- **If the feed narrows over the rounds:** choose **C** (plus **B** if the tiny clips look silly in examples). The original plan still holds.
- **If the feed is flat from the start:** choose **A**. The story becomes "the watch-time recommender gives everyone the same short clips", and Act 3 is about restoring variety for the whole platform.

---

## Final test results (step 2.5)

**What we found:** on the 500 test users, used once, the result is the same as on validation. The model and popularity tie.

| Approach | Prediction error (RMSE) | Liked videos in the top 10 (Precision@10) | Ranking quality (nDCG@10) |
| --- | --- | --- | --- |
| Our model (SVD) | **0.50** | 0.668 → **6.7 of 10** | 0.681 |
| Popularity (same list for everyone) | 0.52 | 0.657 → **6.6 of 10** | 0.675 |
| Guess the average for every video | 0.62 | 0.045 → 0.4 of 10 | 0.043 |

**How to read it:**

- **Liked videos in the top 10:** the model finds about 0.1 more liked video per list than popularity. That's roughly one extra liked video for every ten users. Too small to call a win.
- **Ranking quality (0 to 1, higher is better):** 0.681 vs 0.675, a tie.
- **Prediction error (lower is better):** the model's typical guess is off by 0.50 of a video, against 0.52 for popularity and 0.62 for guessing the average. The model is better at predicting *how much* someone will watch, but that doesn't change *which* videos make the top 10.
- **Validation vs. test:** the numbers are almost the same on both groups of users. That's a good sign: our choice of settings on validation didn't "overfit" (it didn't only work for those particular users).

**What it means for the report:** Act 1 now says "a personalized model trained on watch time ends up recommending what's popular", instead of "the model beats popularity". All numbers are in `results/act1_metrics.csv`.

## How to reproduce these numbers

All numbers use validation users only. From the repo root:

```
python src/model.py time          # speed check (step 2.1)
python src/model.py tune          # tries 20 model settings, about 2 minutes (step 2.4)
python scripts/act1_diagnostics.py   # every table in this document, about 40 seconds
```
