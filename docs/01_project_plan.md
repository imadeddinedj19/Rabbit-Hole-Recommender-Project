# Rabbit Hole Recommender: Step-by-Step Plan

**Status:** draft, waiting for team validation before any coding starts.

**How the documents fit together:**

- [`00_project_proposal.md`](00_project_proposal.md): the *what* and *why* (the three-act story).
- [`PROJECT_SPEC.md`](PROJECT_SPEC.md): the technical spec (data sampling, compute budget, file layout).
- **This file:** the *how* and *in what order*, in plain language, plus two fixes to the spec (marked **⚠ Spec fix**).
- [`02_decisions_log.md`](02_decisions_log.md): every cutoff we choose and why.

---

## How to read this plan

Every step has the same parts:

- **Goal:** what we want out of the step.
- **What we do:** the actual work, in plain language.
- **Output:** the file, chart, or number the step produces. If a step has no output, it didn't happen.
- **Done when:** a simple check so we all agree the step is finished.

New technical terms are in **bold** the first time and explained right there. There's a [glossary](#glossary) at the end.

---

## The big picture in one paragraph

We take real viewing data from a TikTok-like app (KuaiRec). We teach a model to guess how much of each video each user would watch (**Act 1**). Then we let that model "drive" a fake user for 20–30 videos in a row and watch the user's feed shrink into one or two topics (**Act 2**). Finally, we add a "variety knob" to the recommendations and let an optimizer try many settings, to show managers exactly how much watch time they lose for each bit of variety they gain (**Act 3**). We finish with the business question: which setting would *you* pick?

```
Phase 0  Set-up            → shared repo, everyone can run the code
Phase 1  Data              → downsampled train/validation/test files + EDA charts + cutoffs
Phase 2  Act 1: the model  → model beats "just show popular videos"
Phase 3  Act 2: the hole   → line chart of variety collapsing
Phase 4  Act 3: the fix    → Pareto frontier chart
Phase 5  Story             → report + presentation
```

**Compute budget:** the whole pipeline should run in **15–30 minutes on a normal laptop** (see the spec). That's why we downsample the data instead of using all of it.

---

## Phase 0: Set-up (week 1)

### Step 0.1 Shared repository

- **Goal:** one place for all code, charts and documents, so nobody works on an outdated version.
- **What we do:** everyone clones the GitHub repo. Folder layout is in the main [`README.md`](../README.md).
- **Done when:** every teammate has pushed one small change (e.g. their name in the README team table).

### Step 0.2 Same Python environment for everyone

- **Goal:** avoid the "it works on my laptop" problem.
- **What we do:** install `requirements.txt` in a **virtual environment**: a private box of Python libraries just for this project, so it doesn't clash with other courses' projects. Google Colab with the same `requirements.txt` also works.
- **Done when:** `python -c "import pandas, surprise, optuna, pyarrow"` runs without errors.

### Step 0.3 Get the dataset

- **What we do:** run `python scripts/download_data.py`. It downloads `KuaiRec.zip` from Zenodo (the official host linked from the KuaiRec GitHub page) and unzips it into `data/raw/`.
- **The raw data is never committed to GitHub.** `big_matrix.csv` is far above GitHub's 100 MB per-file limit. The repo stores the *script that downloads it* instead, so anyone can rebuild the exact same data with one command. In industry terms: you version the **recipe**, not the ingredients.
- **Done when:** each person can load `small_matrix.csv`.

---

## Phase 1: Data (week 1)

### What's in the box

| File | One row means | Size | We use it for |
| --- | --- | --- | --- |
| `big_matrix.csv` | one user watched one video | 7,176 users × 10,728 videos, 12.5 M rows, **16% filled** | **Training** |
| `small_matrix.csv` | one user watched one video | 1,411 users × 3,327 videos, 4.7 M rows, **99.6% filled** | **Validation + testing** |
| `item_categories.csv` / `kuairec_caption_category.csv` | categories/tags of one video | 10,728 videos | **Diversity** metric and re-ranker |

We only load three columns: `user_id`, `video_id`, `watch_ratio`, stored as compact number types (`int32` / `float32`) to save memory.

**Why "16% filled" vs. "99.6% filled" matters.** Picture a giant spreadsheet: users as rows, videos as columns, each cell says how much of that video the user watched. In the big matrix, 84% of the cells are empty, because people only see a tiny fraction of all videos. That's normal for real platforms, and filling in those blanks is exactly the model's job. In the small matrix almost every cell is filled. That's very rare and it's KuaiRec's superpower: when we test "would this user have liked video X?", we *know* the answer instead of guessing.

### Step 1.1 Downsample (`src/sample.py`)

- **Why:** 12.5 M rows is too slow to tune on a laptop. **Downsampling** means working on a smaller, representative slice. Target: about **1 M training rows**.
- **What we do (spec, with the fix below):**
  1. Keep only the 3,327 videos that appear in the small matrix. The model only needs to know videos we can test on.
  2. Sample **whole users, not random rows**, so each user's viewing history stays intact. (Sampling random rows would give the model scattered fragments of each person's taste.)
  3. Fixed **random seed** (`random_state=42`): the "random" draw is the same every time anyone runs it, so results are reproducible.
  4. Save to `data/processed/` as **Parquet** files (a compressed, fast table format; think "CSV, but 5–10× smaller and faster to load").

> **⚠ Spec fix #1: test users must also be in the training data.**
> The spec samples ~2,000 training users from the big matrix and ~500 test users from the small matrix *independently*. But matrix factorization can only score a user it has *trained on* (it needs their taste profile). If a test user isn't in the training sample, the model falls back to "average user" guesses, and our Act 1 results would mostly measure that fallback. With independent draws, most test users would be missing.
>
> **Fix:** pick the test users **first**, then build the training sample as *their* big-matrix history **plus** randomly chosen other users, up to ~1 M rows.
> - Test users: ~500 from the small matrix → `test.parquet` (their small-matrix rows).
> - Training users: those same users' **big-matrix** rows + extra random big-matrix users → `train.parquet`.
> - This is still a clean test: the model learns a user's taste from what they watched in the big matrix, and is graded on *different* videos in the small matrix.
> - Safety check in code: no `(user_id, video_id)` pair may appear in both train and test. If it did, that would be **data leakage** (the model sees the exam answers during study time). Drop any overlap from train.

> **⚠ Spec fix #2: don't tune on the test set.**
> The spec skips cross-validation "because the small matrix is the holdout". Fine, but if we then pick hyperparameters by their score on that same holdout, the final score is too optimistic. We'd effectively have tuned to the exam.
>
> **Fix:** split the small-matrix users into two disjoint groups:
> - **Validation** (~300 users) → `val.parquet`. Used to *choose* hyperparameters (Act 1) and λ / N (Act 3).
> - **Test** (~500 users) → `test.parquet`. Touched **once**, at the end, for the numbers in the report.
> Both groups' big-matrix histories go into training (fix #1). No extra compute: it's the same data, just labelled differently.

- **Output:** `data/processed/train.parquet`, `val.parquet`, `test.parquet`.
- **Done when:** train ≈ 1 M rows; every val/test user appears in train; zero overlapping (user, video) pairs.

### Step 1.2 Check the sample is representative

- **Goal:** prove the slice looks like the whole, so our conclusions apply to the real data.
- **What we do:** plot the sample vs. the full data side by side: (a) watch ratio histogram, (b) share of videos per category.
- **Output:** one chart for the report (it's in the spec's deliverables).

### Step 1.3 Watch ratio distribution → outlier cap

- **Reminder:** **watch ratio** = time watched ÷ video length. 0.5 = watched half then swiped, 2.0 = watched it twice.
- **Why a cap:** some people leave a video looping while they make coffee, producing watch ratios of 20+. These **outliers** would distort what the model learns, so anything above the **cap** is set to the cap.
- **What we do:** histogram + **percentiles** (the value below which 50%, 90%, 99%, 99.9% of rows fall). Pick a cap between 3 and 5, around the 99th percentile.
- **Output:** chosen cap in the decisions log.

### Step 1.4 Relevance threshold

- **What it is:** the watch ratio above which we count a video as "liked" when grading. The model predicts a number; Precision@10 needs yes/no.
- **What we do:** on the small matrix, check what share of rows is above 1.0, 1.5, 2.0. The proposal starts at **2.0** ("watched twice").
- **Watch out:** if only ~1–2% of rows pass, Precision@10 will be tiny for every model and hard to compare. In that case we discuss lowering it.

### Step 1.5 One category per video → diversity metric

- **Problem:** one video can have **several tags** (e.g. "Food" + "Comedy"), but "unique categories in the top 10" needs exactly one per video.
- **Options:** (1) the **first-level category** in `kuairec_caption_category.csv` (one per video, readable names). *Recommended.* (2) The first tag in `item_categories.csv`. (3) Count all tags (precise, harder to explain).
- **Also check:** how videos spread across categories. If one category holds 40% of all videos, part of any "collapse" is just the catalogue, and we must say so.

### Phase 1 deliverable

`data/processed/*.parquet`, `notebooks/01_data.ipynb` (representativeness + distribution charts), and the decisions log filled in for cap, threshold and category.

---

## Phase 2: Act 1, the model works (weeks 2–3)

### Step 2.1 Calibrate the timing

- Before any real run, time **one** model fit on 100k rows (spec). Multiply up to check the 15–30 min budget holds. If not, reduce the training users.

### Step 2.2 The baseline: "just show the popular videos"

- A **baseline** is the dumbest reasonable solution. If our model can't beat it, it isn't worth anything.
- Rank videos by average watch ratio in the training data; recommend the same top 10 to everyone.

### Step 2.3 The model: matrix factorization (`src/model.py`)

- **Intuition.** Every user has a hidden "taste profile" (likes cooking: a lot; gaming: not really; pets: somewhat) and every video a hidden "content profile" on the same scale. When they match, the user watches more. **Matrix factorization** learns these profiles from watch data alone. Nobody tells it what "cooking" is: it discovers patterns like "people who watch A and B also watch C".
- **Technical version.** Each user and each video becomes a short list of numbers, a **latent factor vector** ("latent" = hidden). Predicted watch ratio ≈ global average + user bias + video bias + **dot product** of the two vectors (multiply position by position, add up). We use `SVD` from the **Surprise** library, trained with **stochastic gradient descent (SGD)**: start with random profiles, look at one known (user, video, watch ratio), nudge the profiles so the prediction gets closer, repeat millions of times.
- **Setup:** input `user_id`, `video_id`; target capped `watch_ratio`. This is **regression** (predict a number, not a class).
- **Scoring trick (spec):** to score every video for every test user, we pull the learned vectors out of the model and do one big matrix multiplication in **NumPy**, instead of asking Surprise one (user, video) pair at a time. Same numbers, roughly 100× faster.

### Step 2.4 Tune the model (hyperparameters)

- **Hyperparameters** are settings *we* choose before training, as opposed to the profiles the model learns. Think oven temperature and baking time vs. the cake.

| Hyperparameter | Plain meaning | Range |
| --- | --- | --- |
| `n_factors` | how many hidden taste dimensions | 20–100 |
| `lr_all` | **learning rate**: how big each nudge is | 0.002–0.01 |
| `reg_all` | **regularization**: penalty that stops the model memorizing noise (**overfitting**) | 0.02–0.1 |
| `n_epochs` | how many passes over the data | 20–50 |

- **How (spec):** 15–20 combinations via **random search** (try random combos in the ranges) or **Optuna** (tries combos smartly, learning from previous tries). No cross-validation.
- **Scored on the validation users** (spec fix #2), not the test users.
- **Output:** table of tried settings + validation RMSE; winner in the decisions log; final model trained once with the winner.

### Step 2.5 Grade the model vs. the baseline (test users, once)

| Metric | Plain meaning | Better is |
| --- | --- | --- |
| **RMSE** | On average, how far off is the predicted watch ratio? | Lower |
| **Precision@10** | Of the 10 videos we'd show, how many did the user actually like? | Higher |
| **nDCG@10** | Like Precision@10, but more credit when liked videos are near the *top* | Higher |

For each test user: score all ~3,300 videos, take the top 10 (excluding videos they watched in training), check against what they really watched in the small matrix.

- **Output:** comparison table for the slides.
- **Done when:** the model clearly beats popularity on Precision@10 and nDCG@10. If it doesn't, stop and debug: Acts 2 and 3 depend on it.

---

## Phase 3: Act 2, the rabbit hole appears (weeks 3–4)

### Step 3.1 The simulated user (`src/simulate.py`)

**The problem it solves:** a brand-new user has no taste profile (the **cold-start problem**), and the trained model doesn't update itself after each video. Without a fix, the feed would never change.

**The fix (spec): fold-in.** We keep all the *video* profiles frozen and only (re)compute the *one* simulated user's profile from what they've watched so far. Technically: find the user vector that best explains their watch history given the fixed video vectors (a small **ridge regression**: a least-squares fit with a regularization penalty). It takes milliseconds. Never retrain the full model.

Each round:

1. Score all videos with the current user profile.
2. Remove already-watched videos (no repeats).
3. Take the top 10 and record how many different categories they contain.
4. The user "watches" the #1 video at a high watch ratio (e.g. 2.0, i.e. "liked it"). Add it to their history, recompute their profile (fold-in).

This creates the **feedback loop** we want to study: you watch cooking → profile moves toward cooking → more cooking recommended → you watch more cooking.

- **Rounds:** 20–30.
- **Many runs:** repeat for 50–100 starting videos spread across categories and plot the **average** curve with a shaded band, so the result isn't one lucky or unlucky example. Still well under a minute.

### Step 3.2 Run and plot

- **Output:** line chart. X: round (1–30). Y: unique categories in the top 10.
- **Expected:** the line drops. **If it doesn't**, that's a real finding, and we report it honestly with an explanation.

---

## Phase 4: Act 3, fix it and optimize the fix (weeks 4–5)

### Step 4.1 The diversity re-ranker: MMR (`src/rerank.py`)

- **Intuition:** a DJ who mostly plays what the crowd likes, but avoids five songs of the same genre in a row.
- **How:** **MMR (maximal marginal relevance)** fills the top 10 one slot at a time. Each remaining candidate gets:

  `score = (1 − λ) × predicted watch ratio − λ × similarity to videos already picked`

  Similarity = 1 if same category, 0 if not. Watch ratio is rescaled to 0–1 first so both halves are comparable.
- **λ (diversity weight):** 0 = pure watch time (Act 2 behaviour), 1 = pure variety.
- **N (candidate pool):** MMR only picks from the model's top N (20–200). Small N = safe but little room to diversify; large N = more variety but riskier picks.
- The re-ranker runs on **stored predictions** (spec): we score once, then re-rank as many times as we like. That's why Act 3 is cheap.

### Step 4.2 Two goals → Optuna → Pareto frontier

- **Why two goals:** with only "maximize watch time", the optimizer would set λ = 0 and switch diversity off.
- **The two objectives**, per (λ, N), averaged over validation users:
  1. **Engagement:** watch ratio of the recommended top 10. *Recommendation:* use the users' **actual** watch ratios from the small matrix (we have them, that's KuaiRec's superpower) rather than the model's own predictions. Otherwise the model grades its own homework. The spec says "predicted"; this is a team decision (see table below).
  2. **Diversity:** unique categories in the top 10.
- **Optuna, ~100 trials, two objectives (multi-objective optimization):** Optuna proposes (λ, N) settings, we score them, it learns where good trade-offs are and returns the **Pareto front** directly.
- **Pareto frontier:** the settings where you can't improve one goal without hurting the other. Everything else is a bad deal (some setting beats it on both). Think of a phone shop: the frontier is the phones where more battery *always* costs more money. Nobody should buy the others.
- **Honest note:** with only two knobs, a plain grid (11 λ values × 4 N values = 44 settings) already maps the trade-off. Optuna mainly adds the "optimizer at work" story and the history plot. The grid is our **fallback**.
- **Outputs:**
  - Optuna optimization history plot (for multi-objective, plot one objective at a time).
  - Pareto scatter (x = diversity, y = engagement), frontier highlighted, three labelled points: *max engagement*, *balanced*, *max diversity*.
  - **Bonus, probably the best slide:** re-run the Act 2 simulation with the *balanced* setting and overlay it on the Act 2 line. Same user, with and without the fix.
- **Final step:** report the three chosen settings' scores on the **test** users.

---

## Phase 5: Report and presentation (weeks 5–6)

- **Freeze results:** every number and chart is produced by code in the repo and saved in `results/`. No chart copy-pasted from someone's laptop that nobody can regenerate.
- **Report** (`report/`), following the three acts: business problem → data and sampling → Act 1 → Act 2 → Act 3 → business and ethics → limitations (simulated user, offline snapshot, downsampled data, category-based diversity).
- **Presentation** (`presentation/`): one chart per idea. Hook (a feed collapsing) → data → Act 1 table → Act 2 line → Act 3 frontier → "which point would you choose?"

---

## Decisions to validate before coding

| # | Decision | Proposed answer | Source |
| --- | --- | --- | --- |
| 1 | Raw data on GitHub? | No, download script | Spec |
| 2 | Downsampling | ~1 M train rows, whole users, seed 42 | Spec |
| 3 | Test users in training data | Yes: their big-matrix history goes into train | **Spec fix #1** |
| 4 | Separate validation users | Yes: ~300 val + ~500 test small-matrix users | **Spec fix #2** |
| 5 | Simulated user | Fold-in, 20–30 rounds, 50–100 starting videos averaged | Spec + plan |
| 6 | Engagement objective in Act 3 | Actual watch ratio (not predicted) | **Plan proposal** |
| 7 | Category definition | First-level category | Phase 1 |
| 8 | Outlier cap / relevance threshold | 3–5 / ~2.0, confirm on data | Phase 1 |
| 9 | Owners per act | To assign: data + model / simulation / optimization / business + slides | Team |

---

## Glossary

| Term | Plain meaning |
| --- | --- |
| Implicit feedback | Learning preferences from behaviour (watching, skipping) instead of ratings |
| Watch ratio | Time watched ÷ video length |
| Sparse / dense matrix | Mostly empty / mostly filled user × video table |
| Downsampling | Working on a smaller, representative slice of the data |
| Random seed | A fixed starting point that makes "random" choices repeatable |
| Train / validation / test | Data to learn from / to choose settings with / to grade once at the end |
| Data leakage | Test information sneaking into training, making results look too good |
| Baseline | The simplest reasonable solution, used as a benchmark |
| Matrix factorization | Learning hidden taste profiles for users and videos from watch data |
| Latent factors | The hidden taste dimensions the model discovers |
| Hyperparameter | A setting chosen before training (vs. what the model learns) |
| Overfitting / regularization | Memorizing noise / a penalty that discourages it |
| Random search / Optuna | Trying random settings / trying settings smartly based on past results |
| RMSE | Average size of the prediction error |
| Precision@K / nDCG@K | How many of the top K were liked / and whether they were near the top |
| Cold start | The model knows nothing about a new user or item |
| Fold-in | Computing one new user's profile while keeping everything else frozen |
| Feedback loop | Recommendations shape behaviour, behaviour shapes the next recommendations |
| MMR | Re-ranking method that balances relevance and variety |
| Multi-objective optimization | Optimizing two or more goals at once |
| Pareto frontier | The set of "best possible trade-offs" between two goals |
