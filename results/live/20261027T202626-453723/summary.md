# Actual live evaluation results

Trials per task/config: 1. No application response cache.

| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|
| A | 80.0% | 80.0% | 3.40 | 7926.3 |
| B | 100.0% | 100.0% | 3.50 | 8344.0 |

## Error analysis

These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.

| Config | Failed assertion | Count |
|---|---|---:|
| A | completed | 1 |
| A | no_recommendation | 3 |
| A | recommended_match | 1 |

## Tasks that changed between configurations

| Task | A observed pass rate | B observed pass rate |
|---|---:|---:|
| missing-duration | 0.0% | 100.0% |
| missing-kind | 0.0% | 100.0% |
| missing-start | 0.0% | 100.0% |
| search-ar-data-riyadh | 0.0% | 100.0% |

With k=1, pass^k equals one-trial performance and does not establish repeated reliability.
No statistical significance claim is made. Examine regressions as well as improvements.
