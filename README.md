# MSU Datathon 2026: Monetizing Trust

Broad Analytics Association case competition at Michigan State University.

Analyze Pulse's monetization options and recommend one strategy or a combination of up to two, balancing revenue, user churn, and trust.

## Project layout

```text
docs/case/          Original case and addendum PDFs
data/raw/           Original datasets (local only; ignored by Git)
data/processed/     Cleaned and derived datasets (generated locally)
notebooks/          Exploratory analysis and modeling notebooks
src/                Reusable analysis code
reports/figures/    Charts and visualizations
reports/slides/     Presentation source and final submission
local/source/       Email transcript and original attachment ZIP (ignored by Git)
```

## Getting started

Datasets are kept local and are not distributed in this public repository. Obtain the original attachments from the organizers and place them in `data/raw/`.

1. Read `docs/case/Datathon_2026_Case.pdf` and the accompanying addendum.
2. Start with `data/raw/all_users_combined.xlsx` for the joined dataset, or join the CSV files on `user_id`.
3. Keep supplied files unchanged in `data/raw/`; write cleaned outputs to `data/processed/`.
4. Record cleaning decisions, assumptions, and analysis in `notebooks/` and reusable code in `src/`.
5. Save figures and the submission deck under `reports/`.

No analysis or software dependencies have been added yet.

## Data availability

The email supplied six attachments: two PDFs, three CSVs, and one Excel workbook. Each CSV contains 20,000 user records. The case also refers to `user_profiles.csv`, which was **not attached**. The combined workbook is described as containing every field; see `data/README.md`.

## Submission

Submit a PDF named `TeamName_Datathon2026.pdf`, with at most 10 slides excluding the title and appendix, by **October 20, 2026 at 11:59 PM**. Follow the addendum for submission instructions and judging criteria.

Case materials and datasets were supplied by the competition organizers; this repository does not grant a license to those materials.
