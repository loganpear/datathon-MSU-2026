# Notebooks

## Initial exploration

Open `01_initial_eda.ipynb` and run the cells from top to bottom. The public notebook contains code and explanations with outputs cleared. Executed copies are kept locally in `local/notebooks/`.

Use Python 3.12 and install the project dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-eda.txt
```

In your notebook editor, select `.venv/bin/python` as the kernel. The local environment is already prepared on the machine where this notebook was created.

The notebook locates the repository from its current directory, reads `data/raw/all_users_combined.xlsx` and the three CSVs, and writes aggregate tables, chart PNGs, and a findings note to `reports/eda/`.

It preserves all raw values. Missing values and range failures are reported, not repaired. Individual user records are not printed in its outputs. Generated reports stay local by default.

The documented range checks follow section 2 of `docs/case/Datathon_2026_Case_Addendum.pdf`. The agreed first-pass cleaning rules are implemented in `src/clean_data.py` and reviewed in `02_data_cleaning.ipynb`.

## Cleaning review

Run `02_data_cleaning.ipynb` after the initial EDA. It calls the same pipeline as `python -m src.clean_data`, writes cleaned data and per-cell logs to `data/processed/`, and shows aggregate quality comparisons. The raw EDA notebook intentionally continues to use raw inputs so the original issues remain visible.

The first pass does not impute numeric values or cap statistical outliers. Select the original analytical fields explicitly; the cleaned dataset also contains provenance flags that should not be included automatically in correlations or models. See `reports/cleaning_summary.md` for the current results and remaining sensitivity analyses.
