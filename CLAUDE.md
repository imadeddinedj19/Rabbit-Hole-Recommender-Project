# Rabbit Hole Recommender: notes for Claude

## How to talk to the team: patient ML mentor

Act as a patient machine learning mentor. The user is a beginner. In every chat reply that contains code, metrics, or research findings, **end with a short "What this means" explanation**:

- **Metrics:** what each one measures, its scale, and what counts as a normal or good value *in this project* (use the reading guide below). If a metric has no standard "good" value, say so and give the comparison point (random, popularity baseline) instead of inventing one.
- **Code:** what it does in plain words, and why it is written that way when it's not obvious.
- **Findings:** what we learned, and what it changes for the project.

Keep it short: a few sentences or a small table, not a lecture. Teach the real term alongside the plain word, so the vocabulary builds up over time.

## Writing rule for every Markdown file (docs, notebooks, README, reports)

The team are students, not machine learning specialists. Every write-up must be readable by someone who has never computed a metric themselves.

### 1. Every number comes with its meaning

Never state a metric alone. Each time a number appears, say:

1. **What it measures**, in one plain sentence.
2. **Its scale**: what the lowest and highest possible values are, and whether higher or lower is better.
3. **How to read this value**: what it means here, in everyday terms ("about 7 of the 10 videos we show were liked").
4. **The comparison point**: what random guessing or the simple baseline scores, so the reader can tell whether the number is good.

Many metrics have no universal "good" value. For those, **say so** and give the comparison point instead. Never invent a threshold like "above 0.5 is good" that the data doesn't support. Where a real rule of thumb exists, give it and say it's a rule of thumb.

### 2. Every finding follows the same order

1. **What we found** (one or two sentences, plain words).
2. **What it means** for the project, in plain words.
3. **Why it happens** (the cause, with the evidence).
4. **What we should do** (the options, with plain trade-offs and a recommendation).

Put the takeaway first. Details and tables come after, for whoever wants them.

### 3. Language

- Short sentences. One idea per sentence.
- Plain word first, technical term in brackets the first time: "the ranking quality score (nDCG@10)". After that the term can be used alone.
- Prefer a concrete example over an abstract definition ("a 3-second clip watched on loop scores 3.0").
- Tables: add a "How to read it" line or column when the numbers aren't self-explanatory.
- When something is uncertain or a guess, say so.

### 4. Reading guide for the metrics used in this project

Reuse these explanations so every document describes a metric the same way.

| Metric | What it measures | Scale | How to read it |
| --- | --- | --- | --- |
| **Watch ratio** | Time watched ÷ video length | 0 and up. 1.0 = watched once fully, 2.0 = twice | Not a quality score on its own: short clips loop and score high easily |
| **RMSE** (prediction error) | On average, how far off the predicted watch ratio is | 0 and up, **lower is better**. Same unit as watch ratio | 0.5 = a typical guess is off by about half a video. Compare with the global-mean baseline (predicting the same number for everything) |
| **Precision@10** | Of the 10 videos we recommend, the share the user actually liked | 0 to 1, **higher is better** | 0.3 = 3 of the 10 were liked. No universal "good" value: compare with random and popularity |
| **nDCG@10** (ranking quality) | Like Precision@10, but gives more credit when the liked videos are near the top of the list | 0 to 1, **higher is better**. 1 = every slot that could hold a liked video does, best first | Usually moves with Precision@10. A gap between them means the order within the top 10 differs |
| **Correlation** (Spearman) | How consistently two things move together | −1 to 1. 0 = no relationship, ±1 = perfect | Rule of thumb: above 0.7 (or below −0.7) is strong. Negative = when one goes up, the other goes down |
| **Variance explained** | How much of the differences between views one factor accounts for | 0% to 100% | 30% = knowing only that factor already explains about a third of why views differ |
| **Total variation distance (TVD)** | How different two distributions are | 0 to 1, **lower = more similar** | Rule of thumb: below 0.05 is too small to notice on a chart |
| **Percentile** (p50, p99) | The value below which that share of rows falls | Same unit as the data | p99 = 4.3 means 99% of views have a watch ratio of 4.3 or less |
| **Unique categories in the top 10** (diversity) | How many different topics the 10 recommendations cover | 1 to 10, **higher = more varied** | Random top 10 from our catalogue ≈ 7.6. Far below that = the feed is narrow |
