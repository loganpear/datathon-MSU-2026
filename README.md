# MSU Datathon 2026: Monetizing Trust

Broad Analytics Association case competition at Michigan State University.

Analyze Pulse's monetization options and recommend one strategy or a combination of up to two, balancing revenue, user churn, and trust.

## Project layout

```text
docs/case/          Original case and addendum PDFs
data/raw/           Original organizer datasets
data/processed/     Cleaned dataset, quality summary, and manifest
notebooks/          Exploratory analysis and modeling notebooks
src/                Reusable analysis code
reports/figures/    Charts and visualizations
reports/slides/     Presentation source and final submission
local/source/       Email transcript and original attachment ZIP (ignored by Git)
```

## Getting started

The original datasets are included in `data/raw/`. The cleaned dataset is in `data/processed/all_users_cleaned.csv`; use it for analysis and retain the original files unchanged.

1. Read `docs/case/Datathon_2026_Case.pdf` and the accompanying addendum.
2. Start with `data/raw/all_users_combined.xlsx` for the joined dataset, or join the CSV files on `user_id`.
3. Keep supplied files unchanged in `data/raw/`; write cleaned outputs to `data/processed/`.
4. Record cleaning decisions, assumptions, and analysis in `notebooks/` and reusable code in `src/`.
5. Save figures and the submission deck under `reports/`.

Initial exploration is available in [`notebooks/01_initial_eda.ipynb`](notebooks/01_initial_eda.ipynb). See [`notebooks/README.md`](notebooks/README.md) for setup and execution instructions. Dependencies are listed in `requirements-eda.txt`.

## Data availability

The email supplied six attachments: two PDFs, three CSVs, and one Excel workbook. Each CSV contains 20,000 user records. The case also refers to `user_profiles.csv`, which was **not attached**. The combined workbook is described as containing every field; see `data/README.md`.

## Submission

Submit a PDF named `TeamName_Datathon2026.pdf`, with at most 10 slides excluding the title and appendix, by **October 20, 2026 at 11:59 PM**. Follow the addendum for submission instructions and judging criteria.

Case materials and datasets were supplied by the competition organizers; this repository does not grant a license to those materials.

## Cleaning the data

After installing `requirements-eda.txt`:

```bash
python -m src.clean_data
python -m unittest discover -s tests -v
```

Review [`notebooks/02_data_cleaning.ipynb`](notebooks/02_data_cleaning.ipynb) for the workflow and [`reports/cleaning_summary.md`](reports/cleaning_summary.md) for aggregate results. Cleaning preserves every user, replaces invalid numeric cells with missing values, labels missing categories `Unknown`, and flags extreme likes without capping. No numeric imputation is applied.

The cleaned dataset, quality summary, and input manifest are included under `data/processed/`. The per-cell change log is generated there locally and remains ignored by Git. Public notebooks contain code and explanations with outputs cleared; executed copies stay in `local/notebooks/`.

## Strategy validation and sensitivity

The independent case model compares all ten allowed strategy combinations and checks the monthly cash path against the existing model. It searches a disclosed grid of simple targeting rules, applies the consent gate for licensing, and tests the selected policy under downside assumptions.

```bash
python -m src.decision_analysis
python -m src.decision_report
```

See [`reports/decision_review.md`](reports/decision_review.md), [`notebooks/03_strategy_validation.ipynb`](notebooks/03_strategy_validation.ipynb), and [`docs/decision_process.md`](docs/decision_process.md). The existing shared deck is linked in `reports/slides/speaker_notes.md`. See `reports/presentation_decision.md` for the selected segment proposal and its acceptance conditions. Results are modeled estimates, and the selected policy is sensitive to brand-contract timing and revenue assumptions.

The deck’s segment proposal is a separate choice from the minimum-loss benchmark: it models 22 funded months at full ad acceptance, with an explicit acceptance and contract gate. Reproduce that check with `python -m src.consent_analysis`.
