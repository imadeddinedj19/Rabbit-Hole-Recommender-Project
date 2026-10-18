# Rabbit Hole Recommender: Project Proposal

Oct 18, 2026 · @Selmane

## The idea

We build a simplified TikTok-style video recommender, show that optimizing only for watch time pushes users into a narrow "rabbit hole" of content, and then find the cheapest way to fix it. The project combines machine learning (predicting what users will watch), automated optimization (tuning the fix), and a business discussion (engagement vs. user wellbeing).

## Research question

**What happens when a recommender optimizes only for watch time, and what does it cost to make it healthier?**

We are not trying to build the most accurate recommender. We are studying how a reasonable model behaves over time and what trade-offs a manager faces when changing it.

## Dataset: KuaiRec

KuaiRec is a public dataset from Kuaishou, a Chinese short-video platform similar to TikTok. It records how real users watched real videos, plus video categories and tags.

- **Key signal: watch ratio** (watch time ÷ video length). This is **implicit feedback**: we infer what people like from behavior, not from ratings.
- **Rare advantage:** its small matrix is almost fully observed (nearly every user saw nearly every video), so our evaluation is more trustworthy than on most datasets.
- **Limitation:** no actual video files. Demos show categories and charts, not clips.

## How it works: three acts

1. **Act 1: The model works.** We train a **matrix factorization** model that predicts each user's watch ratio for each video. It learns hidden "taste dimensions" from viewing patterns. We check it beats a simple baseline: recommending the most popular videos.
2. **Act 2: The rabbit hole appears.** We simulate a new user who watches one video, then let the model recommend and the user "watch" the top pick, repeated 20–30 times. We track how many different categories the user sees. Expected result: variety collapses into one or two categories.
3. **Act 3: We fix it and optimize the fix.** We add a **diversity re-ranker** (MMR) that mixes variety into the top recommendations. A diversity weight (λ) controls how strong the push is. We then use **automated hyperparameter optimization** (grid search or the Optuna library) to test many settings and map the best trade-offs between watch time and diversity, known as the **Pareto frontier**.

The optimizer needs two goals, not one. If we only minimized lost watch time, it would simply switch diversity off.

## Model design

The target variable defines what "good" means, the cutoffs turn it into yes/no decisions, and the hyperparameters are the knobs we tune.

### Variables

- **Target (dependent) variable: watch ratio** = time watched ÷ video length. Below 1 means the user swiped early; above 1 means they rewatched. We train as **regression** (predict the number) and apply a threshold only for evaluation, so the model keeps the difference between a 0.9 and a 0.1.
- **Input (independent) variables:** user ID and video ID. Matrix factorization learns hidden taste dimensions from these alone. Video category and tags are not model inputs; they are used to measure diversity and drive the re-ranker.
- **Outlier handling:** watch ratio is capped at 3–5, so videos left looping don't distort training. Final value set after plotting the distribution in week one.

### Cutoffs

| Cutoff | What it decides | Starting value | Why |
| --- | --- | --- | --- |
| Outlier cap | Max watch ratio used in training | 3–5 | Stops looping videos from distorting the model |
| Relevance threshold | Watch ratio that counts as "liked" in evaluation | \~2.0, confirm on data | Watching twice is a clear sign of interest |
| K (list length) | Recommendations shown and evaluated | 10 | Roughly one scrolling session |
| Simulation rounds | Length of the rabbit hole simulation | 20–30 | Long enough to see the collapse, short enough to plot |
| Diversity constraint | Minimum variety the optimizer must keep | ≥ 4 categories in top 10 | Only if Act 3 uses constrained optimization |

**Train/test split:** train on KuaiRec's big (sparse) matrix, test on the small fully observed matrix, as the dataset is designed.

**Evaluation metrics:** RMSE (prediction error), Precision@10 (share of the 10 recommendations the user liked), nDCG@10 (also rewards placing liked videos near the top).

### Hyperparameters: two separate sets

| Set | Hyperparameter | Typical range | Tuned for | When |
| --- | --- | --- | --- | --- |
| Model | Latent factors (`n_factors`) | 20–100 | Accuracy (RMSE) | Act 1 |
| Model | Learning rate (`lr_all`) | 0.002–0.01 | Accuracy (RMSE) | Act 1 |
| Model | Regularization (`reg_all`) | 0.02–0.1 | Accuracy (RMSE) | Act 1 |
| Model | Epochs (`n_epochs`) | 20–50 | Accuracy (RMSE) | Act 1 |
| System | Diversity weight (λ) | 0–1 | Watch time vs. diversity trade-off | Act 3 |
| System | Candidate pool size (N) | 20–200 | Watch time vs. diversity trade-off | Act 3 |

Model hyperparameters are tuned with grid search and cross-validation, a routine step worth one slide. System hyperparameters are tuned in Act 3 against two goals at once, which produces the Pareto frontier.

**Diversity metric:** number of unique categories in the top 10. Simple to explain on a slide; intra-list diversity (ILD) is the more precise backup if asked.

## Expected results

| Result | What it shows | Format |
| --- | --- | --- |
| Model accuracy vs. popularity baseline | The ML learned real preferences | Small comparison table |
| Diversity over simulation rounds | The rabbit hole effect | Line chart dropping over 20–30 rounds |
| Optimization history | The optimizer finding better settings | Optuna history plot |
| Pareto frontier | The full engagement vs. diversity trade-off | Scatter with 3 highlighted options: max engagement, balanced, max diversity |

Acts 2 and 3 are hypotheses. If the rabbit hole turns out weaker, or diversity costs more than expected, we report that honestly and explain why.

## Business and ethics discussion

The closing argument: an algorithm doing exactly what it was told can still produce outcomes nobody wanted.

- **The incentive:** watch time drives ad revenue, so platforms are paid to maximize it.
- **The long-term risk:** user burnout, churn, and regulation. The European Commission has opened Digital Services Act proceedings against TikTok covering addictive design and rabbit-hole effects.
- **The manager's decision:** the Pareto frontier is a menu, not an answer. We end by asking the audience which point they would choose.

## Risks, limitations, and fallback

- **Simulated user:** real people don't always click the top recommendation. We state this openly.
- **Snapshot data:** offline data can't capture a live platform's feedback loop.
- **Scope creep:** limit optimization to two knobs (diversity weight and candidate pool size). If time runs short, plain grid search still produces the Pareto chart.
- **Framing:** we say "a simplified version of the core idea," never "we built TikTok's algorithm."
- **Fallback:** if KuaiRec is painful to work with in week one, switch to news recommendation (MIND dataset) with the same story.

## Decision for the team

- [ ] Agree on Option 3 (short video, KuaiRec) with this three-act story
- [ ] Agree the optimization layer is part of Act 3, not a separate project
- [ ] Assign one person to load KuaiRec in week one and plot the watch ratio distribution to set the outlier cap and relevance threshold
- [ ] Decide who owns each act: model, simulation, optimization, business slides
