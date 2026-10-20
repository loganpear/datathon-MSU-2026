"""Validate the segment plan and explicit ad-acceptance scenarios for the shared deck.

Acceptance is a hypothetical independent share within each selected segment.
It is not inferred from data-sharing attitude or measured in the case data.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from src.clean_data import clean_dataframe
from src.ml_strategy import segment
from src.decision_analysis import evaluate,INITIAL_CASH,BURN,SCALE

def metrics(revenue):
    cash=INITIAL_CASH+np.cumsum(revenue-BURN)
    failed=np.flatnonzero(cash < -1e-7)
    return {'runway_months':int(failed[0]) if len(failed) else len(cash),
            'cash_month18':float(cash.iloc[17]),'min_cash_through18':float(cash.iloc[:18].min())},cash

def run(root):
    root=Path(root);source=root/'data/raw/all_users_combined.xlsx'
    df,*_=clean_dataframe(pd.read_excel(source,sheet_name='all_users'))
    labels,seg=segment(df)
    open_segment=min(seg['segments'],key=lambda x:x['privacy_sensitivity_score'])['segment']
    casual_segment=min(seg['segments'],key=lambda x:x['engagement_score'])['segment']
    segment_mask=np.isin(labels,[open_segment,casual_segment])
    masks={'Segment plan':segment_mask,'Low-loss threshold':df.ad_targeting_churn_risk.to_numpy()<=.21}
    rows=[];paths=[];scenarios=[]
    for name,mask in masks.items():
        full,full_path=evaluate(df,('ads','brand'),show_mask=mask)
        none,none_path=evaluate(df,('ads','brand'),show_mask=np.zeros(len(df),bool))
        required=max(0.,-none['cash_month18']/(full['cash_month18']-none['cash_month18']))
        for share in [1.,.9,.7]:
            # Combine weighted subpopulations. Non-acceptors retain baseline churn
            # and still contribute brand insights; accepting users face ad churn.
            revenue=full_path.revenue*share+none_path.revenue*(1-share)
            result,cash=metrics(revenue)
            rows.append({'policy':name,'ad_acceptance':share,**result,
                         'extra_users_lost':full['extra_users_lost']*share,
                         'minimum_acceptance_for18':required})
            paths.extend({'policy':name,'ad_acceptance':share,'month':i+1,
                          'revenue':float(revenue.iloc[i]),'cash':float(cash.iloc[i])} for i in range(18))
        scenarios.append({'policy':name,'scenario':'Case assumptions',**full})
        delayed,_=evaluate(df,('ads','brand'),show_mask=mask,brand_delay=3)
        scenarios.append({'policy':name,'scenario':'Brand contracts 3 months later',**delayed})
        _,ad_path=evaluate(df,('ads',),show_mask=mask)
        lower,cash=metrics(full_path.revenue-.2*ad_path.revenue)
        scenarios.append({'policy':name,'scenario':'Ad revenue 20% lower',**lower})
    out=root/'reports/analysis';out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'ad_acceptance.csv',index=False)
    pd.DataFrame(paths).to_csv(out/'ad_acceptance_cash.csv',index=False)
    result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'segments':seg,'target_segments':[open_segment,casual_segment],
            'acceptance_assumption':'Independent hypothetical share among selected users; non-acceptors use baseline churn',
            'existing_plan_scenarios':scenarios}
    (out/'existing_slide_plan.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(pd.DataFrame(rows).to_string(index=False))
    print(pd.DataFrame(scenarios)[['policy','scenario','runway_months','cash_month18']].to_string(index=False))
    return result

if __name__=='__main__':run(Path(__file__).resolve().parents[1])
