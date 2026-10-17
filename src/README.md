# Source code

`clean_data.py` contains the agreed first-pass cleaning rules and writes reproducible local outputs.

```bash
python -m src.clean_data
```

The default project root is derived from the file location. Use `--root /path/to/repo` to supply a different root. The pipeline validates the expected schema and unique user IDs, preserves raw inputs, and records every changed cell. See `data/README.md` and `reports/cleaning_summary.md` for output definitions and results.
