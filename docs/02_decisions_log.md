# Decisions Log

One row per decision. Write *why*, not just *what*: the report and the Q&A will ask.

| Date | Decision | Value | Why | Who |
| --- | --- | --- | --- | --- |
| 2026-10-18 | Raw data on GitHub | No, download script | `big_matrix.csv` exceeds GitHub's 100 MB file limit | |
| | Training sample size | *~1 M rows (confirm after timing run)* | 15–30 min compute budget (spec) | |
| | Test users included in train | *Proposed: yes* | Matrix factorization can't score users it never trained on | |
| | Validation split | *Proposed: ~300 val / ~500 test small-matrix users* | Tuning on the test set inflates results | |
| | Training videos | *Proposed: all videos* | Evaluation users have almost no history on small-matrix videos once test pairs are removed | |
| | Outlier cap on watch ratio | *TBD (3–5)* | Set from 99th percentile | |
| | Relevance threshold | *TBD (~2.0)* | | |
| | Category definition for diversity | *TBD* | | |
| | Engagement objective (Act 3) | *Proposed: actual watch ratio* | Avoids the model grading its own predictions | |
| | Model hyperparameters | *TBD* | | |
