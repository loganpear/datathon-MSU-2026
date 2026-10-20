"""Create aggregate evidence charts from decision results."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.decision_analysis import evaluate,STRESSES
from src.clean_data import clean_dataframe

def run(root):
    root=Path(root);a=root/'reports/analysis';out=root/'reports/figures';out.mkdir(parents=True,exist_ok=True)
    res=json.loads((a/'decision_results.json').read_text())
    table=pd.read_csv(a/'strategy_comparison.csv')
    sensitivity=pd.read_csv(a/'sensitivity.csv')
    raw=pd.read_excel(root/'data/raw/all_users_combined.xlsx',sheet_name='all_users');df,*_=clean_dataframe(raw)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120})
    selected=res['selected_case_policy'];alternative=res['robust_alternative']
    fig,ax=plt.subplots(figsize=(10,5.8))
    rows=table.sort_values('runway_months')
    ax.barh(rows.strategy,rows.runway_months,color=['#0F766E' if v else '#94A3B8' for v in rows.recommendation_eligible])
    ax.axvline(18,color='#A33B33',ls='--',lw=1.5,label='18-month requirement')
    for i,row in enumerate(rows.itertuples()):ax.text(row.runway_months+.15,i,str(row.runway_months),va='center')
    ax.set(xlabel='Modeled funded months',title='All ten strategies under the case assumptions',xlim=(0,21))
    ax.legend(frameon=False,loc='lower right')
    fig.text(.02,.015,'Green: eligible for recommendation. Gray: licensing requires consent not recorded in the dataset.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'strategy_runway.png',dpi=180);plt.close(fig)

    fig,ax=plt.subplots(figsize=(10,5.5))
    traces=[('Ads + brand: case assumptions',selected,{},'#0F766E','-'),
            ('Ads + brand: combined downside',selected,STRESSES['Combined downside'],'#A33B33','--')]
    if alternative:traces.append(('Ads + subscription: combined downside',alternative,STRESSES['Combined downside'],'#4F46A5','-'))
    for name,policy,stress,color,style in traces:
        _,path=evaluate(df,tuple(policy['combo'].split(',')),policy['cap'] or .85,policy['price'] or 4.99,**stress)
        x=[0,*path.month.iloc[:18].tolist()];y=[14,*list(path.cash.iloc[:18]/1e6)]
        ax.plot(x,y,label=name,color=color,ls=style,lw=2.3)
    ax.axhline(0,color='#475569',lw=1);ax.axvline(18,color='#94A3B8',ls=':',lw=1)
    ax.set(xlabel='Months after launch',ylabel='Modeled cash or funding gap ($ millions)',title='The low-churn strategy depends on the brand revenue ramp',xticks=range(0,19,3))
    ax.legend(frameon=False,fontsize=9)
    fig.text(.02,.015,'Negative balances show a hypothetical funding shortfall after insolvency. No recovery financing is assumed.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'cash_sensitivity.png',dpi=180);plt.close(fig)

    fig,ax=plt.subplots(figsize=(10,5))
    display=sensitivity.iloc[:5]
    ax.barh(display.scenario,display.cash_month18/1e6,color=['#0F766E' if v else '#A33B33' for v in display.funded_through_18])
    ax.axvline(0,color='#475569',lw=1)
    ax.set(xlabel='Month-18 cash or hypothetical shortfall ($ millions)',title='Fixed ads-plus-brand policy under disclosed stress assumptions')
    ax.invert_yaxis();fig.tight_layout();fig.savefig(out/'downside_cash.png',dpi=180);plt.close(fig)

    return res

if __name__=='__main__':run(Path(__file__).resolve().parents[1])
