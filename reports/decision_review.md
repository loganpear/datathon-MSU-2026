# Strategy validation and decision review

All results are model scenarios using the supplied case probabilities. Policies and prices are selected on the supplied sample.

## Decision criteria

- Fund every month through month 18. Among feasible grid policies, minimize extra users lost relative to baseline.
- Treat data licensing as a benchmark only until explicit consent exists. Data-sharing attitude is not consent.
- Use simple risk thresholds for an explainable policy. This search does not prove global optimality.

## Comparison of all ten case strategies

| Strategy | Ad risk cap | Price | Runway (months) | Month-18 cash | Extra users lost | Eligible |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Targeted ads | 0.85 |  | 16 | $-911,429 | 684,267 | True |
| Data licensing |  |  | 13 | $-4,967,320 | 1,182,640 | False |
| Subscription |  | $5.49 | 9 | $-11,992,738 | 0 | True |
| Brand insights |  |  | 8 | $-10,596,902 | 0 | True |
| Targeted ads + Data licensing | 0.14 |  | 18 | $385,487 | 1,248,482 | False |
| Targeted ads + Subscription | 0.25 | $5.49 | 18 | $157,400 | 53,927 | True |
| Targeted ads + Brand insights | 0.21 |  | 18 | $319,882 | 32,156 | True |
| Data licensing + Subscription |  | $4.99 | 14 | $-3,083,312 | 1,182,640 | False |
| Data licensing + Brand insights |  |  | 16 | $-1,103,338 | 1,182,640 | False |
| Subscription + Brand insights |  | $5.49 | 10 | $-5,089,640 | 0 | True |

## Leading policy under the case assumptions

Targeted ads + Brand insights, ad-risk cap 0.21. Modeled runway is 18 months, with $319,882 at month 18 and 32,156 extra users lost.

## Fixed-policy sensitivity

These are explicit what-if assumptions, not statistical confidence intervals. Keep targeting and price fixed.

| Scenario | Runway (months) | Month-18 cash | Extra users lost |
| --- | ---: | ---: | ---: |
| Case assumptions | 18 | $319,882 | 32,156 |
| Revenue 10% lower | 15 | $-1,462,106 | 32,156 |
| Brand contracts 3 months later | 13 | $-1,836,855 | 32,156 |
| Extra churn 25% higher | 18 | $131,259 | 45,358 |
| Combined downside | 12 | $-3,561,887 | 45,358 |
| Median-fill missing model inputs | 18 | $334,746 | 32,285 |

## Candidate with a downside buffer

Targeted ads + Subscription, ad-risk cap 0.47, survives all disclosed downside scenarios. Base-case extra users lost: 271,044. Worst minimum cash through month 18: $2,287. This robustness requirement is an additional team assumption and changes the retention tradeoff.

## Additional cash-reserve scenario

No eligible policy in the disclosed grid preserves a $500,000 minimum cash reserve in every downside month through month 18. This reserve is an additional team assumption, not an organizer requirement.

## Interpretation and review

Predictions learn the provided modeled scores. Cross-validation does not establish real-world churn accuracy. The existing decision-tree fidelity measures agreement with its optimizer labels on the training sample. Cash values after the first unfunded month are hypothetical funding shortfalls, not operating cash available to a surviving business. The grid-selected cash buffers are in-sample estimates, not a guarantee. Both partners should review the stress assumptions and the retention-versus-cash tradeoff before final submission.
