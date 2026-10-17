"""Machine-learning and optimization layer for the Pulse monetization case.

Run from the repository root after placing the organizer files in data/raw/:
    python -m src.ml_strategy

Four parts, all on the cleaned data produced in memory by src.clean_data
(raw files are never written):
  1. Segmentation: k-means on user behaviour and attitude scores, k chosen by
     silhouette, then each segment profiled on value and risk.
  2. Predictive models: gradient-boosted models that estimate churn risk and
     value for users who lack those modeled fields (e.g. new sign-ups).
  3. Optimal ad targeting: per-user selection that reaches the runway target
     with the fewest extra users lost (greedy on the exact addendum model).
  4. Explainable policy: a shallow decision tree distilled from the optimal
     targeting, so the rule can be stated on a slide.

User-level outputs go to data/processed/ml/ (ignored by Git). The aggregate
summary goes to reports/ml_summary.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from src.clean_data import clean_dataframe

SEED = 2026

# Case addendum, section 1.
SCALE = 160
CASH = 14_000_000
BURN = 1_750_000
TARGET_MONTHS = 18
HORIZON = 120
DATA_RATE = 0.90
BRAND_RATE = 0.55
RAMP_POINTS = [(0, 0.0), (3, 0.04), (6, 0.11), (8, 0.18), (12, 1.0)]

SEGMENT_FEATURES = ['engagement_score', 'influence_score', 'privacy_sensitivity_score',
                    'trust_score', 'creator_interaction_score', 'community_engagement_score',
                    'subscription_willingness_score']
PROFILE_FIELDS = SEGMENT_FEATURES + [
    'predicted_ad_revenue_per_month', 'max_subscription_price', 'data_value_score',
    'brand_insight_value_score', 'baseline_churn_probability', 'ad_targeting_churn_risk',
    'data_sale_churn_risk', 'subscription_adoption_probability', 'trust_loss_if_ads',
    'trust_loss_if_data_sold']

# Inputs a new user would have without any modeled monetization/risk fields.
PREDICTOR_NUMERIC = ['account_age_months', 'daily_minutes_spent', 'sessions_per_week',
                     'engagement_score', 'influence_score', 'privacy_sensitivity_score',
                     'trust_score', 'posts_per_week', 'likes_per_week', 'shares_per_week',
                     'comments_per_week', 'content_views_per_day', 'creator_interaction_score',
                     'community_engagement_score', 'subscription_willingness_score']
PREDICTOR_CATEGORIES = ['age_group', 'region', 'content_category_preference',
                        'data_sharing_attitude']
PREDICT_TARGETS = ['ad_targeting_churn_risk', 'data_sale_churn_risk',
                   'baseline_churn_probability', 'predicted_ad_revenue_per_month',
                   'subscription_adoption_probability', 'trust_loss_if_ads']

POLICY_FEATURES = ['privacy_sensitivity_score', 'trust_score', 'influence_score',
                   'ad_targeting_churn_risk', 'baseline_churn_probability',
                   'predicted_ad_revenue_per_month', 'trust_loss_if_ads']

COMBOS = [('ads',), ('ads', 'data'), ('ads', 'sub'), ('ads', 'brand')]
PRICES = np.round(np.arange(0.99, 12.0, 0.5), 2)


# ---------------------------------------------------------------- revenue model
def ramp(month: int) -> float:
    """Brand insight share of full revenue in a month (addendum 1.3)."""
    if month >= 12:
        return 1.0
    for (x0, y0), (x1, y1) in zip(RAMP_POINTS, RAMP_POINTS[1:]):
        if month <= x1:
            return y0 + (y1 - y0) * (month - x0) / (x1 - x0)
    return 1.0


def churn_factor(month: int) -> float:
    """Share of a user's churn realized by a month (addendum 1.4)."""
    return min(month, 3) / 3


class Users:
    """Arrays the revenue model needs. Missing values are handled conservatively:
    no ad revenue means not targetable, no max price means not eligible, and
    missing trust loss is left out of trust averages."""

    def __init__(self, df: pd.DataFrame):
        g = lambda c: df[c].to_numpy(dtype=float)
        self.n = len(df)
        self.ad = g('predicted_ad_revenue_per_month')
        self.ad_ok = ~np.isnan(self.ad)
        self.ad = np.nan_to_num(self.ad)
        self.base = g('baseline_churn_probability')
        self.ad_churn = g('ad_targeting_churn_risk')
        self.data_churn = g('data_sale_churn_risk')
        self.max_price = g('max_subscription_price')
        self.adopt = g('subscription_adoption_probability')
        self.data_rev = g('data_value_score') / 100 * DATA_RATE
        self.brand_rev = g('brand_insight_value_score') / 100 * BRAND_RATE
        self.tl_ads = g('trust_loss_if_ads')
        self.tl_data = g('trust_loss_if_data_sold')
        self.influence = g('influence_score')
        self.privacy = g('privacy_sensitivity_score')


def user_terms(u: Users, show_ads: np.ndarray, combo, price, overlap=True):
    """Per-user churn, non-brand monthly revenue, and brand monthly revenue."""
    data, sub, brand = 'data' in combo, 'sub' in combo, 'brand' in combo
    show = show_ads & u.ad_ok if 'ads' in combo else np.zeros(u.n, bool)
    if data:
        churn = np.where(show, np.minimum(1, u.ad_churn + u.data_churn), u.data_churn)
    else:
        churn = np.where(show, u.ad_churn, u.base)
    eligible = sub & (u.max_price >= price) if sub else np.zeros(u.n, bool)
    sub_rev = np.where(eligible, u.adopt * price, 0.0)
    ad_rev = np.where(show, u.ad, 0.0)
    if overlap:
        ad_rev = np.where(eligible, ad_rev * (1 - u.adopt), ad_rev)
    flat = ad_rev + sub_rev + (u.data_rev if data else 0.0)
    brand_rev = u.brand_rev if brand else np.zeros(u.n)
    return churn, flat, brand_rev, show


def simulate(u: Users, show_ads, combo, price=4.99, overlap=True):
    """Month-by-month cash method (addendum 1.5) plus users and trust lost."""
    churn, flat, brand_rev, show = user_terms(u, show_ads, combo, price, overlap)
    s_flat, c_flat = flat.sum(), (flat * churn).sum()
    s_brand, c_brand = brand_rev.sum(), (brand_rev * churn).sum()
    cash, runway, months = CASH, None, []
    for m in range(1, HORIZON + 1):
        f = churn_factor(m)
        rev = ((s_flat - c_flat * f) + (s_brand - c_brand * f) * ramp(m)) * SCALE
        months.append(rev)
        cash += rev - BURN
        if m == TARGET_MONTHS:
            cash_at_target = cash
        if runway is None and cash < 0:
            runway = m - 1
    trust = np.nansum(u.tl_ads[show])
    if 'data' in combo:
        trust += np.nansum(u.tl_data)
    hi_inf = u.influence >= 75
    return {
        'runway_months': HORIZON if runway is None else runway,
        'month1_revenue': months[0], 'month12_revenue': months[11],
        'cash_at_target': cash_at_target,
        'users_lost': churn.sum() * SCALE,
        'extra_users_lost': (churn - u.base).sum() * SCALE,
        'extra_high_influence_lost': (churn - u.base)[hi_inf].sum() * SCALE,
        'avg_trust_loss': trust / u.n,
        'users_shown_ads': int(show.sum()) * SCALE,
    }


# ------------------------------------------------------------ optimal targeting
def optimal_targeting(u: Users, combo, price=4.99, overlap=True, objective='users'):
    """Choose who sees ads so cumulative revenue through the target month covers
    the cash gap, at the least cost in extra churn (objective='users') or trust
    points (objective='trust'). Greedy by revenue gained per unit of cost, which
    is optimal for the linear relaxation and within one user of the integer optimum.
    Returns the mask, or None if showing ads to everyone still falls short."""
    months = range(1, TARGET_MONTHS + 1)
    w0, w1 = TARGET_MONTHS, sum(churn_factor(m) for m in months)
    b0 = sum(ramp(m) for m in months)
    b1 = sum(ramp(m) * churn_factor(m) for m in months)
    value = lambda flat, brand, churn: flat * (w0 - churn * w1) + brand * (b0 - churn * b1)

    everyone, no_one = np.ones(u.n, bool), np.zeros(u.n, bool)
    c1, f1, br1, _ = user_terms(u, everyone, combo, price, overlap)
    c0, f0, br0, _ = user_terms(u, no_one, combo, price, overlap)
    gain = np.where(u.ad_ok, value(f1, br1, c1) - value(f0, br0, c0), -np.inf)
    cost = c1 - c0 if objective == 'users' else np.nan_to_num(u.tl_ads)
    need = (TARGET_MONTHS * BURN - CASH) / SCALE - value(f0, br0, c0).sum()

    free = (gain > 0) & (cost <= 0)
    chosen = free.copy()
    have = gain[free].sum()
    cand = np.flatnonzero((gain > 0) & (cost > 0))
    order = cand[np.argsort(-(gain[cand] / cost[cand]))]
    cum = have + np.cumsum(gain[order])
    if have < need:
        if len(cum) == 0 or cum[-1] < need:
            return None
        k = int(np.searchsorted(cum, need)) + 1
        chosen[order[:k]] = True
    # Monotone cash is assumed above; confirm with the full month-by-month check.
    while simulate(u, chosen, combo, price, overlap)['runway_months'] < TARGET_MONTHS:
        rest = order[~chosen[order]]
        if len(rest) == 0:
            return None
        chosen[rest[: max(1, len(rest) // 200)]] = True
    return chosen


def best_threshold_policy(u: Users, combo):
    """The dashboard's grid search, for comparison with per-user targeting."""
    best = None
    prices = PRICES if 'sub' in combo else [4.99]
    for price in prices:
        for priv in range(10, 101, 10):
            for cap in np.round(np.arange(0.10, 0.851, 0.05), 2):
                mask = (u.privacy <= priv) & (u.ad_churn <= cap)
                r = simulate(u, mask, combo, price)
                meets = r['runway_months'] >= TARGET_MONTHS
                key = (not meets, r['extra_users_lost'] if meets else -r['runway_months'])
                if best is None or key < best[0]:
                    best = (key, {'price': float(price), 'max_privacy': priv,
                                  'max_ad_churn': float(cap), **r, 'meets_target': meets})
    return best[1]


def run_optimization(u: Users):
    results, masks = [], {}
    for combo in COMBOS:
        name = ' + '.join(c.capitalize() if c != 'sub' else 'Subscription' for c in combo)
        for objective in ('users', 'trust'):
            best = None
            for price in (PRICES if 'sub' in combo else [4.99]):
                mask = optimal_targeting(u, combo, price, objective=objective)
                if mask is None:
                    continue
                r = simulate(u, mask, combo, price)
                score = r['extra_users_lost'] if objective == 'users' else r['avg_trust_loss']
                if best is None or score < best[0]:
                    best = (score, price, mask, r)
            row = {'combo': name, 'objective': objective, 'feasible': best is not None}
            if best:
                _, price, mask, r = best
                row.update({'price': float(price) if 'sub' in combo else None, **r})
                masks[(name, objective)] = mask
            results.append(row)
        thr = best_threshold_policy(u, combo)
        results.append({'combo': name, 'objective': 'threshold grid (dashboard)',
                        'feasible': thr['meets_target'], **thr})
    return results, masks


# ----------------------------------------------------------------- segmentation
def describe(z: pd.Series) -> str:
    labels = {'engagement_score': 'engagement', 'influence_score': 'influence',
              'privacy_sensitivity_score': 'privacy sensitivity', 'trust_score': 'trust',
              'creator_interaction_score': 'creator interaction',
              'community_engagement_score': 'community engagement',
              'subscription_willingness_score': 'subscription interest'}
    top = z.abs().sort_values(ascending=False).index[:2]
    return ', '.join(('High ' if z[f] > 0 else 'Low ') + labels[f] for f in top)


def segment(df: pd.DataFrame):
    x = StandardScaler().fit_transform(df[SEGMENT_FEATURES])
    rng = np.random.default_rng(SEED)
    sample = rng.choice(len(x), 5000, replace=False)
    scores = {}
    for k in range(3, 9):
        km = KMeans(k, n_init=10, random_state=SEED).fit(x)
        scores[k] = float(silhouette_score(x[sample], km.labels_[sample]))
    k = max(scores, key=scores.get)
    km = KMeans(k, n_init=10, random_state=SEED).fit(x)
    labels = km.labels_
    z_centers = pd.DataFrame(km.cluster_centers_, columns=SEGMENT_FEATURES)
    total_ad = np.nansum(df['predicted_ad_revenue_per_month'])
    rows = []
    for s in range(k):
        part = df[labels == s]
        prof = part[PROFILE_FIELDS].mean().round(3).to_dict()
        rows.append({
            'segment': s, 'label': describe(z_centers.loc[s]),
            'users_platform': int(len(part) * SCALE), 'share': round(len(part) / len(df), 4),
            'ad_revenue_share': round(float(np.nansum(part['predicted_ad_revenue_per_month']) / total_ad), 4),
            'extra_churn_if_ads': round(float((part.ad_targeting_churn_risk - part.baseline_churn_probability).mean()), 4),
            **prof,
        })
    order = sorted(rows, key=lambda r: -r['ad_revenue_share'])
    return labels, {'k': k, 'silhouette_by_k': scores, 'segments': order}


# ------------------------------------------------------------ predictive models
def predictors(df: pd.DataFrame) -> pd.DataFrame:
    x = df[PREDICTOR_NUMERIC].astype(float)
    cats = pd.get_dummies(df[PREDICTOR_CATEGORIES].astype(str), dtype=float)
    return pd.concat([x, cats], axis=1)


def predictive_models(df: pd.DataFrame):
    x = predictors(df)
    out = []
    for target in PREDICT_TARGETS:
        y = df[target].to_numpy(float)
        keep = ~np.isnan(y)
        xs, ys = x[keep], y[keep]
        r2s, maes = [], []
        for tr, te in KFold(5, shuffle=True, random_state=SEED).split(xs):
            m = HistGradientBoostingRegressor(random_state=SEED).fit(xs.iloc[tr], ys[tr])
            p = m.predict(xs.iloc[te])
            r2s.append(r2_score(ys[te], p))
            maes.append(mean_absolute_error(ys[te], p))
        xtr, xte, ytr, yte = train_test_split(xs, ys, test_size=0.25, random_state=SEED)
        m = HistGradientBoostingRegressor(random_state=SEED).fit(xtr, ytr)
        imp = permutation_importance(m, xte, yte, n_repeats=5, random_state=SEED)
        top = pd.Series(imp.importances_mean, index=xs.columns).sort_values(ascending=False)
        out.append({'target': target, 'cv_r2': round(float(np.mean(r2s)), 3),
                    'cv_r2_sd': round(float(np.std(r2s)), 3), 'cv_mae': round(float(np.mean(maes)), 4),
                    'target_mean': round(float(ys.mean()), 4),
                    'top_drivers': [{'feature': f, 'importance': round(float(v), 4)}
                                    for f, v in top.head(5).items()]})
    return out


# ----------------------------------------------------------- explainable policy
def policy_frame(df: pd.DataFrame) -> pd.DataFrame:
    x = df[POLICY_FEATURES].astype(float)
    x['extra_churn_if_ads'] = x.ad_targeting_churn_risk - x.baseline_churn_probability
    return x


def tree_rules(tree, names) -> list[str]:
    """Plain 'show ads if ...' rules: one per leaf that predicts True, with
    sibling leaves of the same class merged so no split is redundant."""
    t = tree.tree_

    def cls(i):
        if t.children_left[i] == -1:
            return bool(np.argmax(t.value[i][0]) == list(tree.classes_).index(True))
        a, b = cls(t.children_left[i]), cls(t.children_right[i])
        return a if a == b else None

    rules = []

    def walk(i, conds):
        c = cls(i)
        if c is not None:
            if c:
                rules.append(' and '.join(conds) or 'always')
            return
        f, thr = names[t.feature[i]], t.threshold[i]
        walk(t.children_left[i], conds + [f'{f} <= {thr:.3f}'])
        walk(t.children_right[i], conds + [f'{f} > {thr:.3f}'])

    walk(0, [])
    return rules


def distill_policy(df: pd.DataFrame, u: Users, mask: np.ndarray, combo, price):
    """Fit trees of depth 1-3 to the optimal choice and keep the simplest one
    that still reaches the runway target (fidelity alone ignores cash)."""
    x = policy_frame(df)
    keep = u.ad_ok & x.notna().all(axis=1).to_numpy()
    candidates = []
    for depth in (1, 2, 3):
        tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=200, random_state=SEED)
        tree.fit(x[keep], mask[keep])
        pred = np.zeros(u.n, bool)
        pred[keep] = tree.predict(x[keep]).astype(bool)
        r = simulate(u, pred, combo, price)
        candidates.append({'depth': depth, 'fidelity': round(float((pred[keep] == mask[keep]).mean()), 4),
                           'rules': tree_rules(tree, list(x.columns)), 'result': r,
                           'meets_target': r['runway_months'] >= TARGET_MONTHS})
    meeting = [c for c in candidates if c['meets_target']]
    chosen = meeting[0] if meeting else max(candidates, key=lambda c: c['result']['runway_months'])
    return {'chosen_depth': chosen['depth'], 'candidates': candidates}


# ------------------------------------------------------------------------- main
def fmt_money(v):
    return f'${v / 1e6:,.2f}M' if abs(v) >= 1e6 else f'${v / 1e3:,.0f}K'


def write_summary(path: Path, res):
    seg, models, opt, pol = res['segmentation'], res['predictive_models'], res['optimization'], res['policy']
    lines = ['# Machine-learning summary', '',
             'Generated by `python -m src.ml_strategy` from the cleaned data (built in memory from the raw workbook; raw files are not edited). '
             'All figures are platform-wide (sample × 160) and follow the case addendum.', '',
             f'## 1. Segments (k-means, k = {seg["k"]} chosen by silhouette)', '',
             '| Segment | Users | Share of ad revenue | Privacy | Trust | Influence | Extra churn if shown ads |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in seg['segments']:
        lines.append(f'| {s["label"]} | {s["users_platform"]:,} | {s["ad_revenue_share"]:.0%} | '
                     f'{s["privacy_sensitivity_score"]:.0f} | {s["trust_score"]:.0f} | {s["influence_score"]:.0f} | '
                     f'{s["extra_churn_if_ads"]:+.3f} |')
    lines += ['', '## 2. Predictive models for new users (gradient boosting, 5-fold CV)', '',
              'Inputs are profile and behaviour fields only, so these can score a user who has no modeled risk or value fields yet.', '',
              '| Target | CV R² | CV MAE | Top drivers |', '| --- | ---: | ---: | --- |']
    for m in models:
        lines.append(f'| {m["target"]} | {m["cv_r2"]:.3f} ± {m["cv_r2_sd"]:.3f} | {m["cv_mae"]:.4f} | '
                     + ', '.join(d['feature'] for d in m['top_drivers'][:3]) + ' |')
    lines += ['', f'## 3. Optimal ad targeting (reach {TARGET_MONTHS} months at least cost)', '',
              '| Strategy | Method | Price | Runway | Month-1 revenue | Extra users lost | Avg trust loss |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in opt:
        if not r['feasible'] and 'runway_months' not in r:
            lines.append(f'| {r["combo"]} | {r["objective"]} | | not reachable | | | |')
            continue
        price = f'${r["price"]:.2f}' if r.get('price') and 'Subscription' in r['combo'] else ''
        lines.append(f'| {r["combo"]} | {r["objective"]} | {price} | {r["runway_months"]} mo | '
                     f'{fmt_money(r["month1_revenue"])} | {r["extra_users_lost"]:,.0f} | {r["avg_trust_loss"]:.1f} |')
    lines += ['', '`users` minimizes extra users lost; `trust` minimizes trust points lost. '
              'The threshold grid row is the dashboard\'s privacy and churn cutoff search, for comparison.', '',
              f'## 4. Explainable rule for {pol["combo"]} (decision tree distilled from the optimal targeting)', '',
              'Each tree is fitted to the per-user optimal choice. The simplest one that still reaches the runway target is the recommended rule.', '',
              '| Depth | Agreement with optimal | Runway | Extra users lost | Rule: show ads if any line holds |',
              '| ---: | ---: | ---: | ---: | --- |']
    for c in pol['candidates']:
        mark = ' **(chosen)**' if c['depth'] == pol['chosen_depth'] else ''
        lines.append(f'| {c["depth"]}{mark} | {c["fidelity"]:.1%} | {c["result"]["runway_months"]} mo | '
                     f'{c["result"]["extra_users_lost"]:,.0f} | ' + '<br>'.join(f'`{r}`' for r in c['rules']) + ' |')
    lines.append('')
    path.write_text('\n'.join(lines))


def run(root: Path):
    root = Path(root).resolve()
    raw = pd.read_excel(root / 'data/raw/all_users_combined.xlsx', sheet_name='all_users', engine='openpyxl')
    df, *_ = clean_dataframe(raw)
    u = Users(df)

    labels, seg = segment(df)
    models = predictive_models(df)
    opt, masks = run_optimization(u)

    feasible = [r for r in opt if r['objective'] == 'users' and r['feasible']]
    best = min(feasible, key=lambda r: r['extra_users_lost'])
    combo = next(c for c in COMBOS if ' + '.join(x.capitalize() if x != 'sub' else 'Subscription' for x in c) == best['combo'])
    price = best['price'] or 4.99
    policy = {'combo': best['combo'], **distill_policy(df, u, masks[(best['combo'], 'users')], combo, price)}

    out = root / 'data/processed/ml'
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({'user_id': df['user_id'], 'segment': labels}).to_csv(out / 'segments.csv', index=False)
    pd.DataFrame({'user_id': df['user_id'], **{f'{c} | {o}': m for (c, o), m in masks.items()}}) \
        .to_csv(out / 'optimal_ad_targeting.csv', index=False)
    res = {'segmentation': seg, 'predictive_models': models, 'optimization': opt, 'policy': policy}
    (out / 'ml_results.json').write_text(json.dumps(res, indent=2, default=float) + '\n')
    write_summary(root / 'reports/ml_summary.md', res)
    return res


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    res = run(parser.parse_args().root)
    print((Path(parser.parse_args().root) / 'reports/ml_summary.md').read_text())


if __name__ == '__main__':
    main()
