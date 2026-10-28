# Actual live evaluation results

Trials per task/config: 1. No application response cache.

| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|
| B | 100.0% | 100.0% | 4.75 | 14268.5 |

## Error analysis

These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.

| Config | Failed assertion | Count |
|---|---|---:|

With k=1, pass^k equals one-trial performance and does not establish repeated reliability.
No statistical significance claim is made. Examine regressions as well as improvements.
