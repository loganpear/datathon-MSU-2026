# Source code

`clean_data.py` contains the agreed first-pass cleaning rules and writes reproducible local outputs.

```bash
python -m src.clean_data
```

The default project root is derived from the file location. Use `--root /path/to/repo` to supply a different root. The pipeline validates the expected schema and unique user IDs, preserves raw inputs, and records every changed cell. See `data/README.md` and `reports/cleaning_summary.md` for output definitions and results.

`ml_strategy.py` adds the machine-learning and optimization layer: k-means segments, gradient-boosted models that predict churn and value for new users, optimal per-user ad targeting, and a decision-tree rule distilled from it.

```bash
python -m src.ml_strategy
```

It cleans the raw workbook in memory with `clean_data.clean_dataframe`, writes user-level outputs to `data/processed/ml/` (ignored by Git), and writes the aggregate summary to `reports/ml_summary.md`. The dashboard (`dashboard/index.html`) reads `data/processed/ml/ml_results.json` when it's served over http.
