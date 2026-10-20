# Segment proposal and acceptance conditions

The existing deck's segment proposal selects open-engaged and casual-user clusters for ads and pairs them with brand insights. This provides more headroom than the minimum-loss risk-threshold benchmark. It is a conditional proposal, not proof of the lowest possible user loss or a guaranteed outcome.

## Rechecked figures

- At full ad acceptance: 22 funded months, approximately $1.73 million cash at month 18, and 157,500 extra users lost relative to baseline.
- At 90% independent acceptance among selected users: 19 funded months.
- At 70% acceptance: 14 funded months.
- Required acceptance for the 18-month target under the case ramp: approximately 86%.
- Ad-only revenue 20% lower: 16 funded months.
- Brand contracts three months late: 16 funded months.

The deck previously showed 23 months. The corrected figure counts fully funded months and stops when cash first turns negative. The original mid-course subscription fallback was not validated with carried-forward cash and irreversible churn, so the deck does not promise that rescue result.

## What the team still needs to verify

Acceptance is hypothetical and independent within the selected cohort. The supplied data contains no observed ad-consent field. Data-sharing attitude is not consent. Brand revenue follows the organizer ramp and assumes no extra operating costs; signed contracts and privacy safeguards remain implementation conditions.

The minimum-loss threshold benchmark reaches 18 months with about 32,156 extra users lost but needs approximately 97% ad acceptance under the same financial assumptions. The segment proposal gives up some retention to create additional base-case runway. Both partners should understand that tradeoff before submission.

## Reproduction

```bash
python -m src.consent_analysis
```

See `reports/analysis/ad_acceptance.csv`, `ad_acceptance_cash.csv`, and `existing_slide_plan.json`. The existing deck keeps its native slide IDs, original theme, and both partners' names. Speaker notes are in `reports/slides/speaker_notes.md`.
