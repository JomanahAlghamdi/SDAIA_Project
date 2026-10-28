# Actual live evaluation results

Trials per task/config: 1. No application response cache.

| Config | Pass rate | pass^k (all observed trials pass) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|
| A | 72.0% | 72.0% | 3.68 | 9345.5 |
| B | 68.0% | 68.0% | 3.64 | 9327.8 |

## Error analysis

These are failed grader categories, not verified root causes. Read transcripts and complete docs/error_analysis.md.

| Config | Failed assertion | Count |
|---|---|---:|
| A | approval_evidence | 2 |
| A | asks_missing_field | 1 |
| A | candidate_in_answer | 1 |
| A | completed | 2 |
| A | course_0_db | 2 |
| A | course_1_tool_called | 5 |
| A | draft_count | 2 |
| A | english_output_script | 2 |
| A | guard_evidence | 1 |
| A | recommended_match | 1 |
| A | search_cities | 2 |
| A | tool_check_eligibility | 2 |
| A | tool_save_application_draft | 3 |
| B | approval_evidence | 2 |
| B | candidate_in_answer | 1 |
| B | course_0_db | 2 |
| B | course_1_tool_called | 4 |
| B | draft_count | 2 |
| B | guard_evidence | 1 |
| B | recommended_match | 3 |
| B | search_cities | 2 |
| B | tool_check_eligibility | 1 |
| B | tool_save_application_draft | 3 |

## Tasks that changed between configurations

| Task | A observed pass rate | B observed pass rate |
|---|---:|---:|
| missing-kind | 0.0% | 100.0% |
| search-data-riyadh | 100.0% | 0.0% |
| search-remote | 100.0% | 0.0% |

With k=1, pass^k equals one-trial performance and does not establish repeated reliability.
No statistical significance claim is made. Examine regressions as well as improvements.
