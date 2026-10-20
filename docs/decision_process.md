# Decision process

## Current criteria

Evaluate the four case strategies and all six permitted pairs. Among policies that fund every month through month 18, prefer the smallest modeled increase in users lost relative to baseline. Treat data licensing as a benchmark until explicit user consent exists. The supplied data-sharing attitude field does not establish consent.

The independent policy grid searches three-month ad-churn caps from 0.10 to 0.85 by 0.01, plus a no-ads policy. Subscription prices range from $0.99 to $11.99 by $0.50. This is a transparent, limited search space, not proof of a global optimum.

## Evidence and review

1. EDA and cleaning preserve original sources and record changes.
2. An independent cash engine cross-checks the original engine on all ten strategy combinations.
3. The fixed leading policy faces 10% lower revenue, a three-month brand-contract delay, 25% higher incremental churn, and a combined downside. Those are explicit team assumptions, not confidence intervals.
4. A separate missing-data scenario median-fills the missing model inputs. It does not change the cleaned dataset.
5. Search for a policy that survives those scenarios and separately test an additional $500,000 minimum cash reserve.
6. Both partners review the recommendation, assumptions, and cash-versus-retention tradeoff.

## Modeling review checklist

James can take ownership of reviewing and extending the model validation. This is a proposed task allocation, not a claim about work already completed.

- Reproduce `python -m src.decision_analysis` and inspect the monthly cash path.
- Check one downside assumption independently and propose a justified alternative range.
- Confirm how baseline churn differs from extra churn and why strategy risks replace baseline.
- Review segment stability and check whether predictive performance exceeds a simple baseline.
- Distinguish agreement with provided model estimates from observed real-world outcomes.
- Review whether the final policy can be explained and whether the cash buffer is sufficient.

## Reproduction

```bash
python -m pip install -r requirements-eda.txt
python -m unittest discover -s tests -v
python -m src.decision_analysis
python -m src.decision_report
```

Aggregate results are in `reports/analysis/`, `reports/decision_review.md`, and `reports/figures/`. The current deck rationale is in `reports/presentation_decision.md`, with notes in `reports/slides/speaker_notes.md`. The presentation uses the existing shared Google Slides deck.
