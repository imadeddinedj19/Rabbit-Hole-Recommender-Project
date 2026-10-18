# Decisions Log

One row per decision. Write *why*, not just *what*: the report and the Q&A will ask.

| Date | Decision | Value | Why | Who |
| --- | --- | --- | --- | --- |
| 2026-10-18 | Raw data on GitHub | No, download script | `big_matrix.csv` exceeds GitHub's 100 MB file limit | |
| | Training sample size | *~1 M rows (confirm after timing run)* | 15–30 min compute budget (spec) | |
| | Test users included in train | *Proposed: yes* | Matrix factorization can't score users it never trained on | |
| | Validation split | *Proposed: ~300 val / ~500 test small-matrix users* | Tuning on the test set inflates results | |
| | Training videos | *Proposed: all videos* | The big matrix has zero rows for small-matrix users on small-matrix videos (by construction of KuaiRec), so a small-matrix-only filter would leave evaluation users with no history. See `notebooks/01_data.ipynb`, section 1 | |
| | Outlier cap on watch ratio | *Proposed: 4.0, on the model target only* | ≈ p99 of train (4.29). Caps 1.2% of rows and halves the std (1.55 → 0.74). Stays well above the relevance threshold. Notebook section 3 | |
| | Relevance threshold | *Proposed: 2.0 (fallback 1.5)* | 4.7% of validation rows pass (random Precision@10 ≈ 0.05). Median user has 83 liked videos; 1% of users have fewer than 10, none have zero. Notebook section 4 | |
| | Category definition for diversity | *Proposed: first-level category; "Other"/"Unknown" kept as categories* | One per video, readable names. The first tag in `item_categories.csv` disagrees for 1/3 of videos. Largest catalogue category: Local news, 19.7%. Random top 10 ≈ 7.6 categories. Notebook section 5 | |
| | Engagement objective (Act 3) | *Proposed: actual watch ratio* | Avoids the model grading its own predictions | |
| | Model hyperparameters | *TBD* | | |
