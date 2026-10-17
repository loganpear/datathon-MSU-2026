import unittest

import numpy as np
import pandas as pd

from src import ml_strategy as ms


def frame(n=1, **overrides):
    base = {
        'predicted_ad_revenue_per_month': 0.60, 'baseline_churn_probability': 0.10,
        'ad_targeting_churn_risk': 0.30, 'data_sale_churn_risk': 0.40,
        'max_subscription_price': 0.0, 'subscription_adoption_probability': 0.0,
        'data_value_score': 0.0, 'brand_insight_value_score': 0.0,
        'trust_loss_if_ads': 50.0, 'trust_loss_if_data_sold': 60.0,
        'influence_score': 10.0, 'privacy_sensitivity_score': 20.0,
    }
    base.update(overrides)
    return pd.DataFrame({k: [v] * n for k, v in base.items()})


class RevenueModelTests(unittest.TestCase):
    def test_ramp_matches_addendum_table(self):
        table = {1: .013, 2: .027, 3: .04, 4: .063, 5: .087, 6: .11, 7: .145, 8: .18,
                 9: .385, 10: .59, 11: .795, 12: 1, 13: 1}
        for month, share in table.items():
            self.assertAlmostEqual(ms.ramp(month), share, places=3)

    def test_addendum_churn_example(self):
        # Addendum 1.4: $0.60 of ads at 0.30 churn -> $0.54, $0.48, then $0.42.
        u = ms.Users(frame())
        churn, flat, _, _ = ms.user_terms(u, np.array([True]), ('ads',), 4.99)
        got = [flat[0] * (1 - churn[0] * ms.churn_factor(m)) for m in (1, 2, 3, 4)]
        np.testing.assert_allclose(got, [0.54, 0.48, 0.42, 0.42])

    def test_ad_and_data_churn_add_and_cap(self):
        u = ms.Users(frame(ad_targeting_churn_risk=0.7, data_sale_churn_risk=0.6))
        churn, *_ = ms.user_terms(u, np.array([True]), ('ads', 'data'), 4.99)
        self.assertEqual(churn[0], 1.0)

    def test_missing_ad_revenue_is_not_targeted(self):
        u = ms.Users(frame(predicted_ad_revenue_per_month=np.nan))
        churn, flat, _, show = ms.user_terms(u, np.array([True]), ('ads',), 4.99)
        self.assertFalse(show[0])
        self.assertEqual(flat[0], 0.0)
        self.assertEqual(churn[0], 0.10)

    def test_subscribers_stop_generating_ads(self):
        u = ms.Users(frame(max_subscription_price=10.0, subscription_adoption_probability=0.5))
        _, flat, _, _ = ms.user_terms(u, np.array([True]), ('ads', 'sub'), 4.0)
        self.assertAlmostEqual(flat[0], 0.60 * 0.5 + 0.5 * 4.0)

    def test_optimal_targeting_reaches_target_and_prefers_cheap_users(self):
        # Half the users churn heavily on ads; the optimizer should skip them
        # when the cheap half already covers the cash gap.
        n = 2000
        df = pd.concat([frame(n // 2, predicted_ad_revenue_per_month=40.0, ad_targeting_churn_risk=0.12),
                        frame(n // 2, predicted_ad_revenue_per_month=40.0, ad_targeting_churn_risk=0.80)],
                       ignore_index=True)
        u = ms.Users(df)
        mask = ms.optimal_targeting(u, ('ads',))
        self.assertIsNotNone(mask)
        self.assertGreaterEqual(ms.simulate(u, mask, ('ads',))['runway_months'], ms.TARGET_MONTHS)
        self.assertGreater(mask[: n // 2].mean(), mask[n // 2:].mean())

    def test_unreachable_target_returns_none(self):
        u = ms.Users(frame(5))
        self.assertIsNone(ms.optimal_targeting(u, ('ads',)))


if __name__ == '__main__':
    unittest.main()
