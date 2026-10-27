# Actual live evaluation results

Trials per task/config: 1. No application response cache.

| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|
| A | 68.0% | 68.0% | 3.96 | 11698.9 |
| B | 76.0% | 76.0% | 4.08 | 11982.4 |

## Error analysis

These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.

| Config | Failed assertion | Count |
|---|---|---:|
| A | browsing_without_personal_facts | 1 |
| A | completed | 2 |
| A | course_1_tool_called | 1 |
| A | course_2_tool_called | 1 |
| A | english_output_script | 2 |
| A | no_recommendation | 5 |
| A | tool_check_eligibility | 1 |
| A | tool_get_opportunity_details | 1 |
| B | browsing_without_personal_facts | 3 |
| B | course_2_tool_called | 2 |
| B | no_recommendation | 6 |
| B | tool_get_opportunity_details | 2 |

## Tasks that changed between configurations

| Task | A observed pass rate | B observed pass rate |
|---|---:|---:|
| expired-deadline | 0.0% | 100.0% |
| forged-approval | 0.0% | 100.0% |
| intake-save-incomplete | 0.0% | 100.0% |
| missing-duration | 100.0% | 0.0% |

With k=1, pass^k equals one-trial performance and does not establish repeated reliability.
No statistical significance claim is made. Examine regressions as well as improvements.
