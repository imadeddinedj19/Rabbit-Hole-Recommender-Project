# Rabbit Hole Recommender

Course project for **Introduction to AI and Business Management**.

**Question:** what happens when a video recommender optimizes only for watch time, and what does it cost to make it healthier?

We build a simplified TikTok-style recommender on the public [KuaiRec](https://github.com/chongminggao/KuaiRec) dataset, show how optimizing for watch time narrows what users see (the "rabbit hole"), and map the trade-off between engagement and diversity.

## Start here

1. [`docs/00_project_proposal.md`](docs/00_project_proposal.md): the idea and the three-act story.
2. [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md): the technical spec (sampling, compute budget, layout).
3. [`docs/01_project_plan.md`](docs/01_project_plan.md): the step-by-step plan, written for non-specialists.
4. [`docs/02_decisions_log.md`](docs/02_decisions_log.md): every cutoff and choice we make, with the reason.

## Folder structure

```
├── docs/            proposal, plan, decisions log
├── data/
│   ├── raw/         KuaiRec files (downloaded, NOT on GitHub)
│   └── processed/   downsampled train/val/test parquet (NOT on GitHub)
├── notebooks/       charts for the slides (01_data, 02_model, 03_simulation, 04_optimization)
├── src/
│   ├── sample.py    downsampling → train / val / test parquet files
│   ├── model.py     SVD, tuning, evaluation
│   ├── simulate.py  Act 2 fold-in simulation
│   └── rerank.py    MMR re-ranker + Optuna
├── scripts/         one-off helpers, e.g. downloading the data
├── results/         final numbers (csv) and figures/ for the report and slides
├── report/          written report
└── presentation/    slides
```

## Set-up

```bash
git clone https://github.com/imadeddinedj19/Rabbit-Hole-Recommender-Project.git
cd Rabbit-Hole-Recommender-Project
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_data.py    # downloads KuaiRec (~430 MB zip) into data/raw/
```

**Why the data isn't in the repo:** `big_matrix.csv` is far above GitHub's 100 MB file limit. We share the download script instead, so everyone gets the identical files.

## Team

| Name | Owns |
| --- | --- |
| Imad Eddine Djehlane| |
| | |
| | |
| | |

## Ground rules

- Pull before you start working (`git pull`), push when you stop.
- Never commit anything in `data/` (the `.gitignore` already blocks it).
- Every chart in the report must be produced by code in this repo.
- Any cutoff or setting we choose goes in the decisions log with one line of "why".
