"""Conservative, reproducible cleaning of the organizer's combined workbook.

Rules follow the case addendum, section 2. Run from the repository root:
    python -m src.clean_data
Raw inputs are never overwritten. No numeric imputation or capping is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CATEGORIES = {
    'age_group': ['18-24', '25-34', '35-44', '45+'],
    'region': ['North America', 'Europe', 'Asia-Pacific', 'Latin America', 'Other'],
    'content_category_preference': ['Fitness', 'Gaming', 'Fashion', 'Lifestyle', 'Creative'],
    'data_sharing_attitude': ['Restrictive', 'Cautious', 'Neutral', 'Open'],
}
COUNTS = ['account_age_months', 'sessions_per_week', 'posts_per_week',
          'likes_per_week', 'shares_per_week', 'comments_per_week', 'content_views_per_day']
SCORES = ['engagement_score', 'influence_score', 'privacy_sensitivity_score', 'trust_score',
          'creator_interaction_score', 'community_engagement_score',
          'subscription_willingness_score', 'data_value_score', 'brand_insight_value_score',
          'trust_loss_if_data_sold', 'trust_loss_if_ads']
PROBABILITIES = ['baseline_churn_probability', 'ad_targeting_churn_risk',
                 'data_sale_churn_risk', 'subscription_adoption_probability']
DOLLARS = ['predicted_ad_revenue_per_month', 'max_subscription_price']
NUMERIC = COUNTS + SCORES + PROBABILITIES + DOLLARS + ['daily_minutes_spent']
EXPECTED = {'user_id', *CATEGORIES, *NUMERIC}


def clean_dataframe(raw: pd.DataFrame):
    """Return a cleaned copy, cell change log, field audit, and outlier threshold.

    Every source field gets <field>__was_missing. Numeric fields also get
    <field>__was_invalid; categories get <field>__was_unrecognized.
    User IDs/order and valid numeric cells are preserved. Statistical outliers
    are flagged, not changed. Missing numeric values remain missing.
    """
    if set(raw.columns) != EXPECTED:
        raise ValueError(f'Schema mismatch. Missing={EXPECTED - set(raw.columns)}; '
                         f'unexpected={set(raw.columns) - EXPECTED}')
    ids = raw['user_id'].astype('string')
    if ids.isna().any() or ids.duplicated().any() or not ids.str.fullmatch(r'U\d{6}').all():
        raise ValueError('user_id must be unique, nonmissing, and match U followed by six digits.')
    clean = raw.copy(deep=True)
    changes, audit = [], []

    def log_changes(column, mask, reason, replacement):
        for idx in raw.index[mask]:
            value = raw.at[idx, column]
            changes.append({'user_id': raw.at[idx, 'user_id'], 'field': column,
                            'original_value': None if pd.isna(value) else value,
                            'cleaned_value': replacement, 'reason': reason})

    for column in raw.columns:
        if column == 'user_id':
            continue
        missing = raw[column].isna()
        clean[column + '__was_missing'] = missing
        invalid_count = 0
        if column in CATEGORIES:
            # Unknown is our explicit missing-category label, including on repeat runs.
            unexpected = ~missing & ~raw[column].isin([*CATEGORIES[column], 'Unknown'])
            clean[column + '__was_unrecognized'] = unexpected
            clean.loc[missing | unexpected, column] = 'Unknown'
            log_changes(column, missing, 'missing_category', 'Unknown')
            log_changes(column, unexpected, 'unrecognized_category', 'Unknown')
            invalid_count = int(unexpected.sum())
        else:
            values = pd.to_numeric(raw[column], errors='coerce')
            lower, upper = 0, np.inf
            if column in SCORES:
                upper = 100
            elif column in PROBABILITIES:
                upper = 1
            elif column == 'account_age_months':
                lower, upper = 1, 36
            elif column == 'daily_minutes_spent':
                upper = 1440
            parse_failure = ~missing & values.isna()
            nonfinite = values.notna() & ~np.isfinite(values)
            outside = values.notna() & (values.lt(lower) | values.gt(upper))
            fractional = (values.notna() & values.mod(1).abs().gt(1e-9)
                          if column in COUNTS else pd.Series(False, index=raw.index))
            invalid = parse_failure | nonfinite | outside | fractional
            clean[column + '__was_invalid'] = invalid
            # Keep the original dtype/values where possible; replace invalid cells only.
            clean.loc[invalid, column] = np.nan
            invalid_count = int(invalid.sum())
            for idx in raw.index[invalid]:
                reasons = []
                if parse_failure.at[idx]: reasons.append('nonnumeric')
                if nonfinite.at[idx]: reasons.append('nonfinite')
                if outside.at[idx]: reasons.append(f'outside_documented_range_{lower}_{upper}')
                if fractional.at[idx]: reasons.append('fractional_count')
                one_cell = pd.Series(False, index=raw.index)
                one_cell.at[idx] = True
                log_changes(column, one_cell, '; '.join(reasons), None)
        audit.append({'field': column, 'missing_before': int(missing.sum()),
                      'invalid_before': invalid_count,
                      'changed_cells': int((missing.sum() if column in CATEGORIES else 0) + invalid_count),
                      'missing_after': int(clean[column].isna().sum())})

    likes = pd.to_numeric(clean['likes_per_week'], errors='coerce')
    q1, q3 = likes.quantile([.25, .75])
    lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    clean['likes_per_week__iqr_outlier'] = likes.lt(lower) | likes.gt(upper)
    thresholds = {'likes_per_week': {'method': '1.5 * IQR', 'q1': float(q1), 'q3': float(q3),
                                   'lower': float(lower), 'upper': float(upper)}}
    log = pd.DataFrame(changes, columns=['user_id', 'field', 'original_value', 'cleaned_value', 'reason'])
    return clean, log, pd.DataFrame(audit), thresholds


def run_cleaning(root: Path):
    """Write local cleaned data/logs and a shareable aggregate summary."""
    root = Path(root).resolve()
    source = root / 'data/raw/all_users_combined.xlsx'
    output = root / 'data/processed'
    output.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    raw = pd.read_excel(source, sheet_name='all_users', engine='openpyxl')
    clean, log, audit, thresholds = clean_dataframe(raw)
    clean.to_csv(output / 'all_users_cleaned.csv', index=False)
    log.to_csv(output / 'cleaning_changes.csv', index=False)
    audit.to_csv(output / 'cleaning_quality_summary.csv', index=False)
    manifest = {
        'input': 'data/raw/all_users_combined.xlsx', 'sheet': 'all_users',
        'input_sha256': source_hash, 'rows_before': len(raw), 'rows_after': len(clean),
        'original_fields': raw.shape[1], 'output_fields_including_flags': clean.shape[1],
        'changed_cells': len(log), 'users_changed': int(log.user_id.nunique()),
        'numeric_imputation': 'none', 'numeric_missing_after': int(clean[NUMERIC].isna().sum().sum()),
        'category_missing_treatment': 'Unknown', 'outlier_treatment': 'flag only, retain original value',
        'outlier_thresholds': thresholds,
    }
    (output / 'cleaning_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    invalid = audit.loc[audit.invalid_before.gt(0)]
    summary = [
        '# Cleaning summary', '',
        'Rules follow the case addendum, section 2. Raw files were not edited.', '',
        f'- Users retained: **{len(clean):,} / {len(raw):,}**. No rows were dropped.',
        f'- Invalid numeric cells replaced with missing: **{int(audit.loc[audit.field.isin(NUMERIC), "invalid_before"].sum()):,}**.',
        f'- Missing category cells labeled `Unknown`: **{int(audit.loc[audit.field.isin(CATEGORIES), "missing_before"].sum()):,}**.',
        f'- Numeric cells still missing after cleaning: **{manifest["numeric_missing_after"]:,}**. No zeros or medians were substituted.',
        f'- Total changed source cells: **{len(log):,}**, affecting **{manifest["users_changed"]:,}** users.',
        f'- Likes values flagged by 1.5 × IQR: **{int(clean["likes_per_week__iqr_outlier"].sum()):,}**. All retained unchanged.', '',
        '## Invalid cells by field', '', '| Field | Invalid cells |', '| --- | ---: |',
        *[f'| {row.field} | {row.invalid_before} |' for row in invalid.itertuples()], '',
        '## How to use the output', '',
        'Use `data/processed/all_users_cleaned.csv` for analysis. It includes the 30 original fields plus provenance and outlier flags. '
        'For correlations or models, select the intended analytical fields explicitly rather than including all flags.', '',
        'Missing numeric values still need analysis-specific handling. Report observed counts and do not let sums silently imply '
        'complete revenue coverage. Before choosing a strategy, compare conservative and imputed revenue scenarios and test sensitivity '
        'to extreme activity values. Unknown categories preserve users without inventing a demographic or attitude.', '',
        'The per-cell change log, field audit, input hash, and outlier thresholds are stored in `data/processed/`. '
        'The cleaned dataset, field audit, and manifest are versioned; the per-cell change log stays local and is ignored by Git.', '',
    ]
    report = root / 'reports/cleaning_summary.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(summary))
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError('Source hash changed during cleaning.')
    return clean, log, audit, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    _, _, _, manifest = run_cleaning(args.root)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
