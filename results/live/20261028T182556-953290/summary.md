# Actual live evaluation results

Trials per task/config: 1. No application response cache.

| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|
| A | 100.0% | 100.0% | 3.48 | 9760.2 |
| B | 96.0% | 96.0% | 3.68 | 10725.6 |

## Error analysis

These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.

| Config | Failed assertion | Count |
|---|---|---:|
| B | recommended_match | 1 |

## Tasks that changed between configurations

| Task | A observed pass rate | B observed pass rate |
|---|---:|---:|
| search-change-city | 100.0% | 0.0% |

With k=1, pass^k equals one-trial performance and does not establish repeated reliability.
No statistical significance claim is made. Examine regressions as well as improvements.
