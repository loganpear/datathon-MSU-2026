import unittest
import numpy as np
from src import decision_analysis as d
from src import ml_strategy as m
from test_ml_strategy import frame

class DecisionTests(unittest.TestCase):
    def test_independent_engine_agrees_with_original(self):
        df=frame(20,max_subscription_price=10.,subscription_adoption_probability=.2,
                 data_value_score=50.,brand_insight_value_score=60.)
        for combo in d.COMBOS:
            a,_=d.evaluate(df,combo,cap=.5,price=4.99,months=m.HORIZON)
            b=m.simulate(m.Users(df),np.ones(len(df),bool),combo,4.99)
            self.assertAlmostEqual(a['cash_month18'],b['cash_at_target'],places=5)
            self.assertAlmostEqual(a['revenue_month1'],b['month1_revenue'],places=5)
            self.assertAlmostEqual(a['extra_users_lost'],b['extra_users_lost'],places=5)
    def test_churn_example_and_no_repeated_churn(self):
        _,p=d.evaluate(frame(),('ads',),cap=.5,scale=1)
        np.testing.assert_allclose(p.revenue.iloc[:4],[.54,.48,.42,.42])
    def test_cash_zero_counts_as_funded(self):
        x,_=d.evaluate(frame(),(),scale=1)
        self.assertEqual(x['runway_months'],8)
        self.assertFalse(x['funded_through_18'])
    def test_contract_delay_and_revenue_haircut(self):
        df=frame(20,brand_insight_value_score=90)
        _,base=d.evaluate(df,('brand',))
        _,delay=d.evaluate(df,('brand',),brand_delay=3)
        _,half=d.evaluate(df,('brand',),revenue_factor=.5)
        self.assertTrue((delay.revenue.iloc[:3]==0).all())
        np.testing.assert_allclose(half.revenue,.5*base.revenue)
    def test_global_data_policy_and_overlap(self):
        df=frame(2,max_subscription_price=10,subscription_adoption_probability=.5)
        a,_=d.evaluate(df,('ads','sub'),price=4,cap=.5,scale=1)
        self.assertAlmostEqual(a['revenue_month1'],2*(.6*.5+4*.5)*.9)
        b,_=d.evaluate(df,('data',),cap=0,scale=1)
        self.assertAlmostEqual(b['users_lost'],.8)
    def test_later_cash_recovery_does_not_erase_insolvency(self):
        df=frame(20000,brand_insight_value_score=100,baseline_churn_probability=0.)
        row,path=d.evaluate(df,('brand',),scale=180)
        self.assertGreater(row['cash_month18'],0)
        self.assertFalse(row['funded_through_18'])
        self.assertLess(row['runway_months'],18)
    def test_higher_incremental_churn_cannot_improve_cash(self):
        df=frame(20)
        base,_=d.evaluate(df,('ads',))
        stressed,_=d.evaluate(df,('ads',),extra_churn_factor=1.25)
        self.assertGreater(stressed['extra_users_lost'],base['extra_users_lost'])
        self.assertLess(stressed['cash_month18'],base['cash_month18'])
    def test_invalid_combo_rejected(self):
        with self.assertRaises(ValueError):d.evaluate(frame(),('ads','data','sub'))

if __name__=='__main__':unittest.main()
