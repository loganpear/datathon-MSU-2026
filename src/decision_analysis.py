"""Independent cash validation, simple policy search, and fixed-policy stress tests.

Run: python -m src.decision_analysis
All outputs are model scenarios, not observed business outcomes.
"""
from itertools import combinations
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from src.clean_data import clean_dataframe

INITIAL_CASH=14_000_000
BURN=1_750_000
SCALE=160
TARGET=18
NAMES={'ads':'Targeted ads','data':'Data licensing','sub':'Subscription','brand':'Brand insights'}
COMBOS=[(s,) for s in NAMES]+list(combinations(NAMES,2))
PRICES=np.round(np.arange(.99,12,.5),2)
CAPS=np.r_[0., np.round(np.arange(.10,.851,.01),2)]

def schedule(months=60, delay=0):
    return np.interp(np.maximum(np.arange(1,months+1)-delay,0),[0,3,6,8,12],[0,.04,.11,.18,1])

def evaluate(df, combo=(), cap=.85, price=4.99, *, revenue_factor=1., brand_delay=0,
             extra_churn_factor=1., months=60, scale=SCALE, show_mask=None):
    """Independent implementation of addendum 1.2–1.6; returns cash and metrics.

    Missing ad revenue means no ads; missing price means no subscription.
    Missing ad trust loss is zero contribution with explicit coverage counts.
    Financial totals assume the supplied case probabilities, no growth, no extra costs.
    """
    if months<TARGET: raise ValueError('At least 18 months are required.')
    if len(combo)>2 or not set(combo)<=set(NAMES): raise ValueError('Use at most two case strategies.')
    a=lambda c:df[c].to_numpy(float)
    base=a('baseline_churn_probability')
    ad=a('predicted_ad_revenue_per_month'); ad_risk=a('ad_targeting_churn_risk')
    show=(ad_risk<=cap) & np.isfinite(ad) if 'ads' in combo else np.zeros(len(df),bool)
    if show_mask is not None:
        show=np.asarray(show_mask,bool) & np.isfinite(ad) if 'ads' in combo else np.zeros(len(df),bool)
    churn=np.where(show,ad_risk,base)
    if 'data' in combo:
        data_risk=a('data_sale_churn_risk')
        churn=np.where(show,np.minimum(1,ad_risk+data_risk),data_risk)
    # Stress only the increase over baseline. Negative case differences stay as supplied.
    churn=np.clip(churn+np.maximum(churn-base,0)*(extra_churn_factor-1),0,1)
    eligible=(a('max_subscription_price')>=price) if 'sub' in combo else np.zeros(len(df),bool)
    adoption=np.where(eligible,a('subscription_adoption_probability'),0)
    ad_rev=np.where(show,np.nan_to_num(ad),0)*(1-adoption)
    subscription=adoption*price
    licensing=a('data_value_score')*.009 if 'data' in combo else np.zeros(len(df))
    brand=a('brand_insight_value_score')*.0055 if 'brand' in combo else np.zeros(len(df))
    flat=ad_rev+subscription+licensing
    elapsed=np.minimum(np.arange(1,months+1),3)/3
    revenue=((flat.sum()-(flat*churn).sum()*elapsed)
             +(brand.sum()-(brand*churn).sum()*elapsed)*schedule(months,brand_delay))*scale*revenue_factor
    cash=INITIAL_CASH+np.cumsum(revenue-BURN)
    negative=np.flatnonzero(cash < -1e-7)
    trust=a('trust_loss_if_ads'); loss=float(np.nansum(trust[show]))
    if 'data' in combo: loss+=float(np.nansum(a('trust_loss_if_data_sold')))
    results={
        'strategy':' + '.join(NAMES[s] for s in combo) if combo else 'No monetization',
        'cap':float(cap) if 'ads' in combo else None,
        'price':float(price) if 'sub' in combo else None,
        'runway_months':int(negative[0]) if len(negative) else months,
        'funded_through_18':bool((cash[:TARGET]>=-1e-7).all()),
        'cash_month18':float(cash[TARGET-1]),'min_cash_through18':float(cash[:TARGET].min()),
        'revenue_month1':float(revenue[0]),'revenue_month12':float(revenue[11]),
        'users_lost':float(churn.sum()*scale),'extra_users_lost':float((churn-base).sum()*scale),
        'trust_loss_per_user':loss/len(df),'users_shown_ads':int(show.sum()*scale),
        'missing_ad_revenue_users':int(np.isnan(ad).sum()),
        'missing_price_users':int(np.isnan(a('max_subscription_price')).sum()),
        'missing_trust_among_ad_users':int(np.isnan(trust[show]).sum()),
    }
    return results,pd.DataFrame({'month':np.arange(1,months+1),'revenue':revenue,'cash':cash})

def grid(df):
    rows=[]
    for combo in COMBOS:
        best=None
        for price in (PRICES if 'sub' in combo else [4.99]):
            for cap in (CAPS if 'ads' in combo else [.85]):
                result,_=evaluate(df,combo,cap,price)
                # Licensing needs explicit consent, which is not recorded in this dataset.
                result['recommendation_eligible']='data' not in combo
                result['combo']=','.join(combo)
                key=(not result['funded_through_18'],
                     result['extra_users_lost'] if result['funded_through_18'] else -result['runway_months'],
                     -result['cash_month18'])
                if best is None or key<best[0]:best=(key,result)
        rows.append(best[1])
    return pd.DataFrame(rows)

STRESSES={
 'Case assumptions':{},
 'Revenue 10% lower':{'revenue_factor':.9},
 'Brand contracts 3 months later':{'brand_delay':3},
 'Extra churn 25% higher':{'extra_churn_factor':1.25},
 'Combined downside':{'revenue_factor':.9,'brand_delay':3,'extra_churn_factor':1.25},
}

def run(root):
    root=Path(root);raw_path=root/'data/raw/all_users_combined.xlsx'
    raw_hash=hashlib.sha256(raw_path.read_bytes()).hexdigest()
    raw=pd.read_excel(raw_path,sheet_name='all_users');df,*_=clean_dataframe(raw)
    output=root/'reports/analysis';output.mkdir(parents=True,exist_ok=True)
    comparison=grid(df)
    comparison.to_csv(output/'strategy_comparison.csv',index=False)
    eligible=comparison[comparison.recommendation_eligible & comparison.funded_through_18]
    if eligible.empty:raise RuntimeError('No eligible grid policy funds month 18. Report the shortfall.')
    selected=eligible.sort_values(['extra_users_lost','cash_month18'],ascending=[True,False]).iloc[0].to_dict()
    combo=tuple(selected['combo'].split(','));cap=selected['cap'] if 'ads' in combo else .85
    price=selected['price'] if 'sub' in combo else 4.99
    stress=[];paths={}
    for name,params in STRESSES.items():
        res,path=evaluate(df,combo,cap,price,**params);stress.append({'scenario':name,**res});paths[name]=path
    # Freeze the selected policy; missing-data sensitivity must not quietly retune it.
    imputed=df.copy()
    for c in ['predicted_ad_revenue_per_month','max_subscription_price','trust_loss_if_ads']:
        imputed[c]=imputed[c].fillna(imputed[c].median())
    res,_=evaluate(imputed,combo,cap,price);stress.append({'scenario':'Median-fill missing model inputs',**res})
    sensitivity=pd.DataFrame(stress);sensitivity.to_csv(output/'sensitivity.csv',index=False)
    pd.concat([p.assign(scenario=n) for n,p in paths.items()],ignore_index=True).to_csv(output/'cash_paths.csv',index=False)
    # Search an explainable fallback that survives every disclosed downside, if one exists.
    robust=None
    buffered=None
    maximum_buffer=None
    for c in [x for x in COMBOS if 'data' not in x and 'ads' in x]:
        for p in (PRICES if 'sub' in c else [4.99]):
            for k in CAPS:
                base,_=evaluate(df,c,k,p)
                if not base['funded_through_18']:continue
                downs=[evaluate(df,c,k,p,**s)[0] for s in STRESSES.values()]
                worst=min(x['min_cash_through18'] for x in downs)
                if maximum_buffer is None or worst>maximum_buffer['stress_min_cash']:
                    maximum_buffer={**base,'combo':','.join(c),'stress_min_cash':worst}
                if not all(x['funded_through_18'] for x in downs):continue
                candidate={**base,'combo':','.join(c),'stress_min_cash':min(x['min_cash_through18'] for x in downs)}
                if robust is None or base['extra_users_lost']<robust['extra_users_lost']:
                    robust=candidate
                if candidate['stress_min_cash']>=500_000 and (buffered is None or base['extra_users_lost']<buffered['extra_users_lost']):
                    buffered=candidate
    manifest={'source_sha256':raw_hash,'sample_users':len(df),'scale':SCALE,
              'objective':'Minimize extra users lost among policies funding all first 18 months',
              'consent_policy':'Licensing is benchmark-only; explicit consent is not recorded',
              'selection_scope':'Simple ad-risk thresholds on disclosed grid; not a global optimum',
              'selected_case_policy':selected,'robust_alternative':robust,'buffered_alternative':buffered,
              'cash_reserve_assumption':500000,'maximum_grid_downside_buffer':maximum_buffer,'stress_assumptions':STRESSES,
              'limitations':['Modeled case estimates, not observed churn or causal effects',
                  'In-sample policy selection; scenario sensitivity is not deployment validation',
                  'No new users or additional operating costs per the addendum',
                  'Missing ad and subscription revenue contributes zero in the conservative case',
                  'Unknown consent is not inferred from data-sharing attitude']}
    def json_ready(value):
        if isinstance(value,dict):return {k:json_ready(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [json_ready(v) for v in value]
        if isinstance(value,(float,np.floating)) and not np.isfinite(value):return None
        return value
    manifest=json_ready(manifest)
    (output/'decision_results.json').write_text(json.dumps(manifest,indent=2,default=float,allow_nan=False)+'\n')
    lines=['# Strategy validation and decision review','',
      'All results are model scenarios using the supplied case probabilities. Policies and prices are selected on the supplied sample.','',
      '## Decision criteria','',
      '- Fund every month through month 18. Among feasible grid policies, minimize extra users lost relative to baseline.',
      '- Treat data licensing as a benchmark only until explicit consent exists. Data-sharing attitude is not consent.',
      '- Use simple risk thresholds for an explainable policy. This search does not prove global optimality.','',
      '## Comparison of all ten case strategies','',
      '| Strategy | Ad risk cap | Price | Runway (months) | Month-18 cash | Extra users lost | Eligible |',
      '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for row in comparison.to_dict('records'):
        cap_text=f'{row["cap"]:.2f}' if pd.notna(row['cap']) else ''
        price_text=f'${row["price"]:.2f}' if pd.notna(row['price']) else ''
        lines.append(f'| {row["strategy"]} | {cap_text} | {price_text} | {row["runway_months"]} | ${row["cash_month18"]:,.0f} | {row["extra_users_lost"]:,.0f} | {row["recommendation_eligible"]} |')
    lines+=['','## Leading policy under the case assumptions','',
      f'{selected["strategy"]}, ad-risk cap {cap:.2f}. Modeled runway is {selected["runway_months"]} months, '
      f'with ${selected["cash_month18"]:,.0f} at month 18 and {selected["extra_users_lost"]:,.0f} extra users lost.','',
      '## Fixed-policy sensitivity','',
      'These are explicit what-if assumptions, not statistical confidence intervals. Keep targeting and price fixed.','',
      '| Scenario | Runway (months) | Month-18 cash | Extra users lost |','| --- | ---: | ---: | ---: |']
    for row in stress:lines.append(f'| {row["scenario"]} | {row["runway_months"]} | ${row["cash_month18"]:,.0f} | {row["extra_users_lost"]:,.0f} |')
    if robust:
        lines+=['','## Candidate with a downside buffer','',
          f'{robust["strategy"]}, ad-risk cap {robust["cap"]:.2f}, survives all disclosed downside scenarios. '
          f'Base-case extra users lost: {robust["extra_users_lost"]:,.0f}. '
          f'Worst minimum cash through month 18: ${robust["stress_min_cash"]:,.0f}. '
          'This robustness requirement is an additional team assumption and changes the retention tradeoff.']
    else:lines+=['','## Downside result','','No policy in the eligible simple-policy grid survives every disclosed downside. Do not present the 18-month target as guaranteed.']
    if buffered:
        lines+=['','## Additional cash-reserve scenario','',
          f'With a team-selected $500,000 minimum reserve in every downside month through month 18, the lowest-churn grid policy is '
          f'{buffered["strategy"]}, cap {buffered["cap"]:.2f}, price ${buffered["price"]:.2f}. '
          f'Base-case extra users lost: {buffered["extra_users_lost"]:,.0f}. '
          f'The $500,000 reserve is a sensitivity assumption, not an organizer requirement.']
    else:
        lines+=['','## Additional cash-reserve scenario','','No eligible policy in the disclosed grid preserves a $500,000 minimum cash reserve in every downside month through month 18. This reserve is an additional team assumption, not an organizer requirement.']
    lines+=['','## Interpretation and review','','Predictions learn the provided modeled scores. Cross-validation does not establish real-world churn accuracy. '
      'The existing decision-tree fidelity measures agreement with its optimizer labels on the training sample. '
      'Cash values after the first unfunded month are hypothetical funding shortfalls, not operating cash available to a surviving business. '
      'The grid-selected cash buffers are in-sample estimates, not a guarantee. '
      'Both partners should review the stress assumptions and the retention-versus-cash tradeoff before final submission.','']
    (root/'reports/decision_review.md').write_text('\n'.join(lines))
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest()==raw_hash
    return manifest

if __name__=='__main__':
    result=run(Path(__file__).resolve().parents[1])
    print(json.dumps({'selected':result['selected_case_policy'],'robust':result['robust_alternative'],'buffered':result['buffered_alternative']},indent=2,allow_nan=False))
