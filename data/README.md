# Data

`raw/` preserves the original downloaded attachments locally. The datasets are ignored by Git and are not included in the public repository. Place organizer-provided copies here:

| File | Records | Columns |
| --- | ---: | ---: |
| engagement_behavior.csv | 20,000 | 8 |
| monetization_potential.csv | 20,000 | 6 |
| risk_and_churn_metrics.csv | 20,000 | 7 |
| all_users_combined.xlsx | See `all_users` sheet | Combined data |

The workbook contains `Start here` and `all_users` sheets. The addendum describes it as the four datasets pre-joined on `user_id`.

`user_profiles.csv` is mentioned in the case and email but was not among the six attachments. Do not treat a reconstructed file as an original organizer attachment.

Preserve blanks and outliers in raw inputs. Record cleaning decisions and place generated files in `processed/`, which is ignored by Git.

## Cleaned outputs

Run `python -m src.clean_data` from the repository root to create:

- `processed/all_users_cleaned.csv`: the original 30 fields plus provenance flags.
- `processed/cleaning_changes.csv`: one row per changed cell, including user ID, field, original value, replacement, and reason.
- `processed/cleaning_quality_summary.csv`: field-level missingness and validity counts.
- `processed/cleaning_manifest.json`: source hash, policy details, and outlier thresholds.

All these files stay local. Raw files are never overwritten. Flags ending in `__was_missing` identify original blanks; `__was_invalid` identifies numeric cells replaced by missing values; `__was_unrecognized` identifies unsupported category labels; `likes_per_week__iqr_outlier` flags values outside 1.5 times the interquartile range without changing them.

`Unknown` is an explicit missing category, not an imputed demographic value. Numeric gaps remain missing for analysis-specific treatment. Flag columns are metadata, not additional user characteristics to feed automatically into a model.
