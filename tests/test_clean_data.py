"""Boundary and preservation checks using synthetic users, never organizer records."""
import unittest

import numpy as np
import pandas as pd

from src.clean_data import CATEGORIES, NUMERIC, clean_dataframe


def sample(n=4):
    data = {'user_id': [f'U{i:06d}' for i in range(n)]}
    data.update({column: [allowed[0]] * n for column, allowed in CATEGORIES.items()})
    data.update({column: [.5 if 'probability' in column or column.endswith('_risk') else 10.] * n
                 for column in NUMERIC})
    return pd.DataFrame(data)


class CleaningTests(unittest.TestCase):
    def test_missing_categories_numeric_and_original_preservation(self):
        raw = sample()
        raw.loc[0, 'region'] = None
        raw.loc[1, 'predicted_ad_revenue_per_month'] = np.nan
        raw.loc[2, 'max_subscription_price'] = 0
        before = raw.copy(deep=True)
        clean, log, _, _ = clean_dataframe(raw)
        pd.testing.assert_frame_equal(raw, before)
        self.assertEqual(clean.loc[0, 'region'], 'Unknown')
        self.assertTrue(clean.loc[0, 'region__was_missing'])
        self.assertTrue(pd.isna(clean.loc[1, 'predicted_ad_revenue_per_month']))
        self.assertEqual(clean.loc[2, 'max_subscription_price'], 0)
        self.assertEqual(len(log), 1)
        pd.testing.assert_series_equal(clean.user_id, raw.user_id)

    def test_documented_boundaries_and_invalid_cells(self):
        raw = sample()
        raw['account_age_months'] = [1, 36, 0, 37]
        raw['daily_minutes_spent'] = [0, 1440, -1, 1441]
        raw['baseline_churn_probability'] = [0, 1, -.01, 1.01]
        raw['trust_score'] = [0, 100, -.1, 100.1]
        raw['sessions_per_week'] = [0, 10, 1.5, np.inf]
        clean, log, audit, _ = clean_dataframe(raw)
        for column in ['account_age_months', 'daily_minutes_spent', 'baseline_churn_probability',
                       'trust_score', 'sessions_per_week']:
            self.assertTrue(clean.loc[[2, 3], column].isna().all(), column)
            pd.testing.assert_series_equal(clean.loc[[0, 1], column], raw.loc[[0, 1], column], check_dtype=False)
            self.assertTrue(clean.loc[[2, 3], column + '__was_invalid'].all())
            self.assertFalse(clean.loc[[2, 3], column + '__was_missing'].any())
        self.assertEqual(len(log), 10)
        self.assertEqual(int(audit.invalid_before.sum()), 10)

    def test_extreme_values_are_flagged_not_capped(self):
        raw = sample(100)
        raw.loc[99, 'likes_per_week'] = 100000
        clean, _, _, _ = clean_dataframe(raw)
        self.assertTrue(clean.loc[99, 'likes_per_week__iqr_outlier'])
        pd.testing.assert_series_equal(clean.likes_per_week, raw.likes_per_week)

    def test_unrecognized_category_and_nonnumeric_cell(self):
        raw = sample()
        raw.loc[0, 'region'] = 'Invalid region'
        raw['trust_score'] = raw.trust_score.astype(object)
        raw.loc[0, 'trust_score'] = 'not a score'
        clean, log, _, _ = clean_dataframe(raw)
        self.assertEqual(clean.loc[0, 'region'], 'Unknown')
        self.assertTrue(clean.loc[0, 'region__was_unrecognized'])
        self.assertTrue(pd.isna(clean.loc[0, 'trust_score']))
        self.assertEqual(len(log), 2)

    def test_already_cleaned_source_fields_are_not_edited_again(self):
        raw = sample()
        raw.loc[0, 'region'] = None
        raw.loc[1, 'daily_minutes_spent'] = -5
        first, _, _, _ = clean_dataframe(raw)
        second, log, _, _ = clean_dataframe(first[raw.columns])
        self.assertTrue(log.empty)
        pd.testing.assert_frame_equal(first[raw.columns], second[raw.columns])

    def test_duplicate_ids_and_missing_schema_are_rejected(self):
        raw = sample()
        raw.loc[1, 'user_id'] = raw.loc[0, 'user_id']
        with self.assertRaisesRegex(ValueError, 'user_id'):
            clean_dataframe(raw)
        with self.assertRaisesRegex(ValueError, 'Schema mismatch'):
            clean_dataframe(sample().drop(columns='trust_score'))


if __name__ == '__main__':
    unittest.main()
