# Cleaning summary

Rules follow the case addendum, section 2. Raw files were not edited.

- Users retained: **20,000 / 20,000**. No rows were dropped.
- Invalid numeric cells replaced with missing: **19**.
- Missing category cells labeled `Unknown`: **440**.
- Numeric cells still missing after cleaning: **1,039**. No zeros or medians were substituted.
- Total changed source cells: **459**, affecting **457** users.
- Likes values flagged by 1.5 × IQR: **612**. All retained unchanged.

## Invalid cells by field

| Field | Invalid cells |
| --- | ---: |
| account_age_months | 9 |
| daily_minutes_spent | 5 |
| sessions_per_week | 5 |

## How to use the output

Use `data/processed/all_users_cleaned.csv` for analysis. It includes the 30 original fields plus provenance and outlier flags. For correlations or models, select the intended analytical fields explicitly rather than including all flags.

Missing numeric values still need analysis-specific handling. Report observed counts and do not let sums silently imply complete revenue coverage. Before choosing a strategy, compare conservative and imputed revenue scenarios and test sensitivity to extreme activity values. Unknown categories preserve users without inventing a demographic or attitude.

The per-cell change log, field audit, input hash, and outlier thresholds are stored in `data/processed/`. The cleaned dataset, field audit, and manifest are versioned; the per-cell change log stays local and is ignored by Git.
