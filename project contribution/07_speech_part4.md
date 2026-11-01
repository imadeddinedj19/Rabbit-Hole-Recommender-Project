# Part 4 speech: the Video Nutrition Label

**Presenter:** Imad eddine Djehlane · **Length:** about 5 minutes · **Order:** slide 21 → live app → slide 22 → slide 23

## Structure in one line

**Problem → data → features → benchmark → AI layer (and its failure) → population findings → deployment → feasibility**

---

## Opening (on Lu's slide 20)

> Parts 2 and 3 looked at the platform side: how the recommender decides what you see. Part 4 looks at the user side.
>
> Today the only feedback a user gets is a single number: screen time. That number tells you *how much* you watched, not *what*. Our proposal is a **video nutrition label**: a per-user summary of viewing behaviour, built from the same interaction logs the platform already collects.

## Slide 21: "same calories, different diet"

> **The data.** We used the KuaiRec interaction log from Kuaishou: 12.5 million viewing events, about 7,000 users, 28 days. Each row is one user, one video, the seconds watched, the video length, and a timestamp. Every video has one of 39 platform categories.
>
> **The features.** For each user we computed a small set of indicators, the same way you would engineer features before training any model:
> - volume: videos per day;
> - composition: the share of watch time per category;
> - concentration: how many categories make up 80% of the time;
> - replays: seconds watched after the clip already played once in full;
> - night viewing, quick swipes, and the longest session without a 30-minute break.
>
> Think of it as the label on a bottle: volume is the calories, categories are the ingredients, replays are the added sugar.
>
> **Why composition matters.** These two users watch **76** and **77** videos a day. On screen-time alone they are identical. But the first spends **39%** of their time in one category, more concentrated than **96%** of users. The second's largest category is **10%**, spread over 16 categories. Same volume, completely different consumption profile. A screen-time metric cannot see that difference; the label can.

## Live app: the prototype

*(switch to `01_label_prototype.html`, already on "The narrow diet")*

> This is the prototype, running on the real data.
>
> **Benchmarking.** There is no clinical threshold for a "healthy" amount of short video, so we don't invent one. Every line is benchmarked against the population instead, as a percentile. For example: "replays: 49% of time, higher than 93% of users."
>
> *(click "The heavy viewer")* This user is at the 95th percentile: **137 videos a day**, with one session of **341 videos** without a 30-minute break.
>
> **One data-quality decision.** The reference population is **5,765 users**, not 7,000. KuaiRec holds out part of the history of its 1,411 test users to prevent leakage in recommender evaluation. That's correct for Parts 2 and 3, but it makes those users look artificially light. So we excluded them from the benchmark.
>
> *(point at the AI box)* **The AI layer.** We used Google Gemini, a large language model, for one narrow task: turning the label into a three-sentence plain-language summary. The model never sees the viewing history, only the computed numbers. **The numbers are computed; the AI only explains them.**
>
> **What went wrong.** In the first version we sent raw numbers without units. The model hallucinated meaning. "10 videos" became "10 minutes". "Higher than 90% of users" became "90% more than other users".
>
> **The fix had two parts:**
> - **Structured prompting:** every fact is sent pre-labelled, with its unit and its comparison.
> - **An automated fact check:** every number in the output must exist in the input.
>
> Result: **101 of 101** summaries passed. Same lesson as Part 3: the LLM is useful as an explainer, but only with controlled input and a validation step.

## Slide 22: "what 5,765 labels tell us"

*(back to the slides)*

> Once every user has a label, we can also read the population. Two findings.
>
> **Left: replays are everywhere.** **28%** of all watch time is replays: seconds spent on a clip that already played once in full. It isn't one category driving it. Every major category sits between 21% and 33%, and Local news is the highest. That's a design effect, autoplay and looping, not a content effect.
>
> **Right: heavier users are not narrower.** We split users into five groups by volume, from about 37 to about 120 videos a day. The share of time in their top category goes *down* slightly, from 24% to 19%. The correlation is weak and negative, −0.24. Heavy users don't fall into one topic; they watch more of everything, and more at night: 21% of their time, against 9% for the lightest group.
>
> The implication for the label: for most people, the important lines are **volume, session length and night viewing**, not only variety. A label that only measured diversity would miss the heavy users.

## Slide 23: "three moments, one clock"

> **Deployment.** The label is only useful at the right touchpoint. We designed three:
> 1. **In-session:** a passive counter. Videos so far, dominant category. No blocking.
> 2. **At a user-defined limit:** the feed pauses and shows the composition of that session. One tap continues. The user sets the threshold, not the platform.
> 3. **Next morning:** the full label with the AI summary, outside the feed.
>
> **Feasibility.** The platform could ship all three immediately: every metric we used is already in its logs, and the computation is simple aggregation, no new model needed. A third party is limited. It can build the morning report from the user's data export (GDPR right of access, Art. 15, and data portability, Art. 20). It cannot run inside the mobile app, and it cannot change the ranking.
>
> So the barrier is not technical. It's the incentive: a label adds friction to a business model that is optimised for watch time.

## Closing

> To sum up: we didn't build a better recommender. We built a measurement layer on the user's side: engineered features from interaction logs, benchmarked against the population, explained by an LLM with guardrails.
>
> The platform already has the bottle and every ingredient. It just doesn't print the label.

---

## Cheat card (print this)

```
PROBLEM   screen time = only "how much", never "what"
DATA      KuaiRec: 12.5M events · ~7k users · 28 days · 39 categories
FEATURES  volume · category share · concentration (80%) · replays · night · swipes · longest session
S21       76 vs 77 videos/day → 39% one category (>96% of users) vs 10% over 16 → same volume, different profile
APP       benchmark = percentiles, no invented threshold
          heavy viewer: 137/day (95th pct), 341 in one session
          reference = 5,765 users (1,411 test users excluded: held-out history)
AI        Gemini, input = label numbers only → v1 hallucinated units/percentiles
          → v2 structured prompt + automated fact check → 101/101 passed
S22       replays 28% of all time, 21–33% in every category → design effect, not content
          heavier users NOT narrower: top category 24% → 19% (r = −0.24) · night 9% → 21%
          → label must show volume, sessions, night, not only variety
S23       in-session · at user-set limit · next morning
          platform: can ship now (simple aggregation) · third party: export only (GDPR Art. 15/20)
          barrier = incentive, not technology
CLOSE     "measurement layer on the user side" · "has every ingredient, doesn't print the label"
```

## Before you start

- Open `01_label_prototype.html` in a browser tab, on "The narrow diet".
- Don't use the dropdown of shared users (incomplete data).
- The app works offline.

## Likely questions

**"How reliable is the data?"**
> KuaiRec logs only part of each user's viewing: logged play time is about 4% of session time. So we rely on counts and shares, not minutes. That's why the main unit is videos per day.

**"Why use an LLM at all, if the numbers are computed?"**
> For accessibility. A table of percentiles isn't readable for most users; three sentences are. The LLM is deliberately restricted to explanation, and every output is validated.

**"Why would a platform adopt this?"**
> Regulatory pressure: the DSA already covers recommender transparency, and the EU is investigating addictive design. The implementation cost is low; the real cost is potential lost watch time, which is a business decision, not a technical one.
