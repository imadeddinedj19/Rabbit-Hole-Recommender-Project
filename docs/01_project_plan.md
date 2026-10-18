# Rabbit Hole Recommender: Step-by-Step Plan

**Status:** draft, waiting for team validation before any coding starts.
**Read this first:** [`00_project_proposal.md`](00_project_proposal.md) (the *what* and *why*). This file is the *how* and *in what order*.

---

## How to read this plan

Every step has the same four parts:

- **Goal:** what we are trying to get out of the step.
- **What we do:** the actual work, in plain language.
- **Output:** the file, chart, or number the step produces. If a step has no output, it didn't happen.
- **Done when:** a simple check so we all agree the step is finished.

New technical terms are in **bold** the first time and explained right there. There is also a [glossary](#glossary) at the end.

---

## The big picture in one paragraph

We take real viewing data from a TikTok-like app (KuaiRec). We teach a model to guess how much of each video each user would watch (**Act 1**). Then we let that model "drive" a fake user for 20–30 videos in a row and watch the user's feed shrink into one or two topics (**Act 2**). Finally, we add a "variety knob" to the recommendations and let an optimizer try many settings, to show managers exactly how much watch time they lose for each bit of variety they gain (**Act 3**). We finish with the business question: which setting would *you* pick?

```
Phase 0  Set-up            → shared repo, everyone can run the code
Phase 1  Know the data     → charts + the cutoffs we were unsure about
Phase 2  Act 1: the model  → model beats "just show popular videos"
Phase 3  Act 2: the hole   → line chart of variety collapsing
Phase 4  Act 3: the fix    → Pareto frontier chart
Phase 5  Story             → report + presentation
```

---

## Phase 0: Set-up (week 1)

### Step 0.1 Shared repository and folders

- **Goal:** one place where all code, charts, and documents live, so nobody works on an outdated version.
- **What we do:** everyone clones the GitHub repo and works on it. The folder layout is described in the main [`README.md`](../README.md).
- **Output:** the repo with the folder structure.
- **Done when:** every teammate has cloned the repo and pushed one small change (for example, adding their name to the team table in the README).

### Step 0.2 Same Python environment for everyone

- **Goal:** avoid the classic "it works on my laptop" problem.
- **What we do:** install the libraries listed in `requirements.txt` in a **virtual environment**. A virtual environment is a private box of Python libraries for this project only, so it doesn't clash with other courses' projects.
- **Output:** a working environment on each laptop (or everyone uses Google Colab with the same `requirements.txt`).
- **Done when:** `python -c "import pandas, surprise, optuna"` runs without errors.

### Step 0.3 Get the dataset

- **Goal:** everyone has the same KuaiRec files in `data/raw/`.
- **What we do:** run `python scripts/download_data.py`. It downloads `KuaiRec.zip` from Zenodo (the official host) and unzips it into `data/raw/`.
- **Important:** the raw data is **not stored on GitHub**. The main file (`big_matrix.csv`) is far over GitHub's 100 MB per-file limit, and the full zip is several hundred MB. Instead, the repo stores the *script that downloads it*. Anyone can rebuild the exact same data with one command. This is standard practice in industry: you version the **recipe**, not the ingredients.
- **Output:** `data/raw/KuaiRec 2.0/data/*.csv` on each laptop.
- **Done when:** each person can load `small_matrix.csv` and sees about 4.7 million rows.

---

## Phase 1: Get to know the data (week 1)

This phase is called **EDA (exploratory data analysis)**: looking at the data with simple charts before building anything. It's where we fix the "to be confirmed" values from the proposal.

### What's in the box

| File | What one row means | Size (approx.) | We use it for |
| --- | --- | --- | --- |
| `big_matrix.csv` | one user watched one video | 7,176 users × 10,728 videos, 12.5 M rows, **16% filled** | **Training** the model |
| `small_matrix.csv` | one user watched one video | 1,411 users × 3,327 videos, 4.7 M rows, **99.6% filled** | **Testing** the model |
| `item_categories.csv` | the tags of one video | 10,728 videos | Measuring **diversity** |
| `kuairec_caption_category.csv` | caption + category names of one video | 10,728 videos | Human-readable category names for charts |
| `user_features.csv`, `item_daily_features.csv`, `social_network.csv` | extra info | | **Not used** (out of scope) |

Columns of the two matrices: `user_id, video_id, play_duration, video_duration, time, date, timestamp, watch_ratio`.

**Why "16% filled" vs. "99.6% filled" matters.** Picture a giant spreadsheet: users as rows, videos as columns, and each cell says how much of that video the user watched. In the big matrix, 84% of the cells are empty, because people only see a tiny fraction of all videos. That's normal for real platforms, and it's exactly what the model has to learn to fill in. In the small matrix, almost every cell is filled. That's very rare and it's KuaiRec's superpower: when we test "would this user have liked video X?", we actually *know* the answer instead of guessing.

### Step 1.1 Check the data loads correctly

- **What we do:** load each file, count rows, users, videos, and missing values. Check that the users and videos in the small matrix also appear in the big matrix (they should).
- **Output:** `notebooks/01_eda.ipynb`, first section.
- **Done when:** our counts match the table above.

### Step 1.2 Plot the watch ratio distribution → set the outlier cap

- **Reminder:** **watch ratio** = time watched ÷ video length. 0.5 means "watched half then swiped", 2.0 means "watched it twice".
- **What we do:** histogram of `watch_ratio`, and a table of **percentiles** (the value below which 50%, 90%, 99%, 99.9% of rows fall).
- **Why:** some people leave a video looping while they go make coffee, producing watch ratios of 20+. Those are **outliers**, values so extreme they'd distort what the model learns. We **cap** them: anything above the cap is set to the cap.
- **Decision rule (proposal):** pick a cap between 3 and 5, roughly where the 99th percentile sits.
- **Output:** histogram + chosen cap written in `docs/02_decisions_log.md`.

### Step 1.3 Set the relevance threshold

- **What it is:** the watch ratio above which we say "the user *liked* this video" when we grade the model. The model predicts a number; the grade needs yes/no.
- **What we do:** on the small matrix, check what share of rows are above 1.0, 1.5, 2.0. The proposal starts at **2.0** (the KuaiRec authors also use 2.0 as their "like" signal).
- **Watch out:** if only ~1–2% of rows pass the threshold, Precision@10 will be tiny for every model and hard to compare. In that case we discuss lowering it.
- **Output:** chosen threshold + one sentence of justification in the decisions log.

### Step 1.4 Decide what "category" means → the diversity metric

- **Problem we need to settle:** in `item_categories.csv` one video can have **several tags** (e.g. "Food" and "Comedy"). "Number of unique categories in the top 10" needs exactly one category per video.
- **Options:**
  1. Use the **first-level category** from `kuairec_caption_category.csv` (one per video, has readable names). *Recommended.*
  2. Use the first tag in `item_categories.csv`.
  3. Count all tags (more precise, harder to explain).
- **What we do:** count how many categories exist and how videos spread across them (bar chart). If one category holds 40% of all videos, "variety collapsing" could just reflect the catalogue, and we need to say so.
- **Output:** bar chart of videos per category + decision in the log.

### Phase 1 deliverable

`notebooks/01_eda.ipynb` + `docs/02_decisions_log.md` with: outlier cap, relevance threshold, category definition.

---

## Phase 2: Act 1, the model works (weeks 2–3)

### Step 2.1 The baseline: "just show the popular videos"

- **What it is:** a **baseline** is the dumbest reasonable solution. If our fancy model can't beat it, the fancy model isn't worth anything.
- **What we do:** rank videos by their average watch ratio in the big matrix. Recommend the same top 10 to everyone.
- **Output:** the baseline's scores (see Step 2.4).

### Step 2.2 The model: matrix factorization

- **Intuition first.** Think of each user as having a hidden "taste profile" (likes cooking: a lot; likes gaming: not really; likes pets: somewhat) and each video as having a hidden "content profile" on the same scale. If the two profiles match, the user watches a lot of the video. **Matrix factorization** learns these profiles automatically from the watch data alone. Nobody tells it what "cooking" is. It discovers patterns like "people who watch A and B also tend to watch C".
- **Technical version.** Each user and each video becomes a list of numbers called a **latent factor vector** ("latent" = hidden, not directly observed). The predicted watch ratio is roughly the **dot product** of the two vectors (multiply them position by position and add up), plus a few bias terms such as "this user watches everything longer than average". We use the `SVD` algorithm from the **Surprise** library, which trains with **stochastic gradient descent (SGD)**: start with random profiles, look at one known (user, video, watch ratio), nudge the profiles a little so the prediction gets closer, repeat millions of times.
- **Setup:**
  - Input: `user_id`, `video_id`. Target: capped `watch_ratio`. This is **regression** (we predict a number, not a class).
  - **Train on big matrix, test on small matrix**, as KuaiRec is designed.
  - Make sure no (user, video) pair appears in both train and test. Otherwise the model gets "exam questions it has already seen", which is called **data leakage**.
- **Output:** `src/model.py` + trained model.

### Step 2.3 Tune the model (hyperparameters)

- **What hyperparameters are:** settings *we* choose before training, as opposed to the profiles the model learns itself. Think of the oven temperature and baking time vs. the cake.
- **Which ones:** `n_factors` (how many taste dimensions), `lr_all` (how big each nudge is: the **learning rate**), `reg_all` (**regularization**: a penalty that stops the model from memorizing noise, i.e. **overfitting**), `n_epochs` (how many passes over the data).
- **How:** **grid search with cross-validation**. Grid search = try every combination from a small list. Cross-validation = split the training data into e.g. 3 parts, train on 2 and score on the 3rd, rotate, and average, so one lucky split doesn't fool us.
- **Practical warning:** the big matrix has 12.5 M rows. A full grid (4 × 4 × 4 × 3 = 192 combos × 3 folds) would take far too long on a laptop. **Plan:** tune on a random 10–20% sample of the big matrix with a small grid (~12–20 combos), then train once on the full big matrix with the winner. We say this openly in the report.
- **Output:** a table of tried settings and their RMSE; the chosen settings in the decisions log.

### Step 2.4 Grade the model vs. the baseline

| Metric | Plain meaning | Better is |
| --- | --- | --- |
| **RMSE** (root mean squared error) | On average, how far off is the predicted watch ratio? | Lower |
| **Precision@10** | Of the 10 videos we'd show this user, how many did they actually like (above the relevance threshold)? | Higher |
| **nDCG@10** | Like Precision@10, but also gives more credit when the liked videos are near the *top* of the list | Higher |

How we grade: for each user in the small matrix, the model scores all ~3,300 videos, we take its top 10, and we check against what the user really watched. (This is only possible because the small matrix is almost full.)

- **Note:** the popularity baseline has no RMSE in the usual sense (it predicts the same thing for everyone), so we can compute it using each video's average, but Precision@10 and nDCG@10 are the fairer comparison.
- **Output:** the comparison table for the slides.
- **Done when:** the model clearly beats popularity on Precision@10 and nDCG@10. If it doesn't, we stop and debug before moving on, because Acts 2 and 3 depend on it.

---

## Phase 3: Act 2, the rabbit hole appears (weeks 3–4)

### Step 3.1 Design the simulated user (needs a team decision)

The proposal says "a new user watches one video, then watches the top pick, 20–30 times". There's a technical catch we must solve first:

**The cold-start problem.** Matrix factorization only has taste profiles for users it saw during training. A brand-new user has no profile, so the model can't recommend anything to them. Also, the trained model doesn't update itself after each video, so without a fix the "feed" would never change.

**Proposed solution (simple and explainable):** build the simulated user's taste profile as the **average of the profiles of the videos they've watched so far**. After each round, the newly watched video is added to the average. This creates the **feedback loop** we want to study: you watch cooking → profile moves toward cooking → more cooking is recommended → you watch more cooking.

Each round:

1. Score all videos with the current user profile.
2. Remove videos already watched (no repeats).
3. Take the top 10. Record how many different categories they contain.
4. The user "watches" the #1 video. Add it to their history and update the profile.

- **Alternative:** start from a *real* user in the small matrix instead of a blank user. More realistic, slightly more complex. Can be a second chart if time allows.
- **Run it many times:** do the simulation for 50–100 different starting videos (from different categories) and plot the **average** curve, so the result isn't one lucky or unlucky example.

### Step 3.2 Run and plot

- **Output:** line chart. X-axis: round (1–30). Y-axis: number of unique categories in the top 10 (average over all runs, with a shaded band for spread).
- **Expected:** the line drops. **If it doesn't**, that's a real finding. We report it honestly and explain why (for example, the model may already favour popular videos from many categories).

---

## Phase 4: Act 3, fix it and optimize the fix (weeks 4–5)

### Step 4.1 The diversity re-ranker (MMR)

- **Intuition:** a DJ who mostly plays what the crowd likes, but avoids playing five songs of the same genre in a row.
- **How it works:** **MMR (maximal marginal relevance)** builds the top 10 one slot at a time. For each slot, every remaining candidate gets the score:

  `score = (1 − λ) × predicted watch ratio − λ × similarity to videos already picked`

  "Similarity" here = 1 if same category, 0 if not (simple and explainable). Watch ratio must be put on a 0–1 scale first so both parts are comparable.
- **λ (lambda), the diversity weight:** 0 = pure watch time (Act 2 behaviour), 1 = pure variety.
- **N, the candidate pool size:** MMR only picks from the model's top N videos (e.g. 50). Small N = safe, but less room to diversify. Large N = more variety, but may include videos the user won't watch.

### Step 4.2 Two goals at once → the Pareto frontier

- **Why two goals:** if we only told the optimizer "maximize watch time", it would just set λ = 0 and switch diversity off. We must ask for both.
- **The two scores** for each (λ, N) setting, measured on the small matrix:
  1. **Engagement:** average real watch ratio of the recommended top 10.
  2. **Diversity:** average number of unique categories in the top 10 (and/or at the end of the rabbit-hole simulation).
- **Pareto frontier:** the set of settings where you can't improve one goal without hurting the other. Everything else is a "bad deal" (another setting is better on both). Think of a phone shop: the frontier is the phones where getting more battery *always* costs more money. The rest you'd never buy.
- **How we search:**
  - **Grid search** first: λ in {0, 0.1, …, 1.0} × N in {20, 50, 100, 200} = 44 settings. Cheap and already enough to draw the chart. This is the **fallback** if anything goes wrong.
  - **Optuna** (optional upgrade): a library that tries settings smartly instead of exhaustively, and supports two goals at once (**multi-objective optimization**). It gives us the "optimization history" plot from the proposal.
- **Output:** scatter plot (x = diversity, y = engagement), frontier highlighted, three labelled options: *max engagement*, *balanced*, *max diversity*.
- **Bonus chart:** re-run the Act 2 simulation with the "balanced" setting and overlay it on the Act 2 line. This is probably the single most convincing slide: the same user, with and without the fix.

---

## Phase 5: Report and presentation (weeks 5–6)

### Step 5.1 Freeze the results

- All final numbers and charts are produced by code in the repo and saved in `results/`. No chart copy-pasted from someone's laptop that nobody can regenerate.

### Step 5.2 Report (`report/`)

Suggested structure, following the three acts:

1. Introduction: the business problem (engagement vs. wellbeing, DSA proceedings against TikTok).
2. Data: KuaiRec, why the fully observed matrix matters, our cutoffs and why.
3. Act 1: model, baseline, results table.
4. Act 2: simulation design, rabbit-hole chart.
5. Act 3: MMR, Pareto frontier, the three options.
6. Business and ethics discussion: the manager's decision.
7. Limitations: simulated user, offline snapshot, simple category-based diversity.

### Step 5.3 Presentation (`presentation/`)

One chart per idea. Suggested flow: hook (a feed collapsing) → data → Act 1 table → Act 2 line chart → Act 3 frontier → "which point would you choose?" to the audience.

---

## Decisions the team needs to validate before coding

| # | Decision | Proposed answer | Decided in |
| --- | --- | --- | --- |
| 1 | Raw data on GitHub? | **No.** Download script instead (file size limits) | Now |
| 2 | Python environment | Local virtual env *or* Google Colab, same `requirements.txt` | Now |
| 3 | Simulated user design | Profile = average of watched videos' profiles; 50–100 runs averaged | Now |
| 4 | Category definition | First-level category from `kuairec_caption_category.csv` | Phase 1 |
| 5 | Outlier cap | 3–5, set from the 99th percentile | Phase 1 |
| 6 | Relevance threshold | 2.0, lower if too few positives | Phase 1 |
| 7 | Model tuning scope | Small grid on a 10–20% sample | Phase 2 |
| 8 | Optimizer | Grid search first, Optuna if time allows | Phase 4 |
| 9 | Owners per act | To assign: data + model / simulation / optimization / business + slides | Now |

---

## Glossary

| Term | Plain meaning |
| --- | --- |
| Implicit feedback | Learning preferences from behaviour (watching, skipping) instead of explicit ratings (stars, likes) |
| Watch ratio | Time watched ÷ video length |
| Sparse / dense matrix | Mostly empty / mostly filled user × video table |
| Baseline | The simplest reasonable solution, used as a benchmark |
| Matrix factorization | Learning hidden taste profiles for users and videos from watch data |
| Latent factors | The hidden taste dimensions the model discovers |
| Hyperparameter | A setting chosen before training (vs. what the model learns) |
| Overfitting | Memorizing the training data instead of learning general patterns |
| Regularization | A penalty that discourages overfitting |
| Cross-validation | Scoring a model on several different train/validation splits and averaging |
| Data leakage | When test information sneaks into training, making results look too good |
| RMSE | Average size of the prediction error |
| Precision@K / nDCG@K | How many of the top K recommendations were liked / and whether they were near the top |
| Cold start | The model knows nothing about a new user or item |
| Feedback loop | Recommendations shape behaviour, behaviour shapes the next recommendations |
| MMR | Re-ranking method that balances relevance and variety |
| Pareto frontier | The set of "best possible trade-offs" between two goals |
| Multi-objective optimization | Optimizing for two or more goals at once |
