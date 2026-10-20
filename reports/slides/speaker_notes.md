# Presentation speaker notes

[Existing Google Slides deck](https://docs.google.com/presentation/d/137lXJYsOD_VhgvJlWjgDuiDDANUHsy4l5a8C-QtORfQ/edit)

The deck presents the segment proposal as a conditional launch strategy. The minimum-loss risk-threshold policy remains a comparison benchmark.

## 1. Monetizing Trust A selective ads and brand insights proposal

James Williams and Logan Pearson. All financial and user-loss figures are modeled estimates under the supplied case assumptions. The segment plan produces 22 fully funded months at full ad acceptance. Acceptance is not observed. Source: src/consent_analysis.py; reports/analysis/existing_slide_plan.json.

## 2. The financial target

Initial cash 14,000,000. Monthly burn 1,750,000. Flat required revenue = 1,750,000 - 14,000,000/18 = 972,222.22. This shortcut does not replace the monthly cash path. A month ending at exactly zero counts as funded. Once cash first turns negative, later hypothetical revenue does not restore operating solvency without financing.

## 3. Data preparation and validation

Raw inputs are unchanged. There are 1,039 missing numeric cells after cleaning. The conservative financial scenarios assume zero contribution for 60 missing ad-revenue records and no subscription eligibility for 100 missing max-price records. A median-fill sensitivity is separate and does not alter the cleaned dataset. Extreme likes are retained and flagged. The predictive models use supplied modeled scores as targets, not observed outcomes.

## 4. Four behavior and attitude segments

Source: src/ml_strategy.py segment(); src/consent_analysis.py. Deterministic seed 2026, k-means n_init 10. Silhouette for k=4 is approximately 0.400 on a sampled set of 5,000 users. Names summarize cluster profiles, not inferred consent. We do not claim age or region is uniform without a separate demographic test.

## 5. Creators face larger increases in ad churn

Creator baseline 4.2% versus ad churn 45.7%, about 41.5 percentage points extra. Privacy-sensitive baseline 5.9% versus 55.7%, about 49.8 points extra. These are case estimates, not an experiment or causal result. The segment proposal shows no ads to creator or privacy-sensitive clusters; those users still face baseline churn. Protecting them does not mean zero total user loss.

## 6. No single strategy reaches 18 months

Source: reports/analysis/strategy_comparison.csv. The grid searches ad-risk caps and subscription prices described in docs/decision_process.md. This is a limited policy search, not a global optimum. No-ads baseline runway is 8 months. Brand licensing revenue is 0.55 times score/100 at full ramp. Data licensing is 0.90 times score/100.

## 7. More cash headroom can cost more users

Source: reports/analysis/strategy_comparison.csv, existing_slide_plan.json, decision_results.json. The two-segment plan is the existing deck proposal, with corrected monthly solvency arithmetic. The 18-month low-loss threshold is a useful retention benchmark. The subscription buffer option survives the chosen combined downside with only about $2,287 minimum cash, so it is not a large safety cushion. No eligible grid policy preserves a $500,000 minimum reserve in every stress month. That reserve is a team sensitivity assumption, not an organizer requirement.

## 8. Proposal: selective ads plus brand insights

The proposal targets the clusters with the lowest average privacy sensitivity and lowest average engagement, corresponding to Open engaged and Casual users. Users with missing ad revenue do not receive ads. At full acceptance, 2,044,800 platform-scaled users receive ads. Total modeled users lost are 499,026, including baseline loss of approximately 341,525. Extra loss is approximately 157,500. Approximately 86% independent ad acceptance is needed to fund all 18 months under the case ramp. Consent is not measured or inferred from attitude. Sources: src/consent_analysis.py, ad_acceptance.csv, existing_slide_plan.json.

## 9. Ad acceptance changes the cash path

Acceptance scenarios combine a share of selected users receiving ads with a complementary group receiving no ads and retaining baseline churn. Both groups can contribute brand insight revenue, with their respective survival probabilities. Acceptance is assumed independent within the selected cohort. At 100% acceptance the segment plan funds 22 months. At 90%, 19 months. At 70%, 14 months. The required acceptance share is approximately 85.98% for 18 funded months. No acceptance rate is observed in the supplied case data. The graph focuses on the 18-month target period.

## 10. Launch gates and downside risks

Source: src/consent_analysis.py. Independent monthly calculations yield 22 funded months for the two selected clusters at full acceptance, 16 for a three-month brand delay, and 16 for a 20% haircut to ad-only revenue. A mid-course switch to subscription would require a new stateful simulation carrying forward cash and irreversible churn. A fresh-start subscription scenario cannot establish the result of that switch. Launch planning should validate ad acceptance, signed brand contracts, and financing needs. Brand insight privacy safeguards require separate review. The absence of a brand-specific trust-loss field does not establish zero real-world harm.
