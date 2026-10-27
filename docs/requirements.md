# Course requirement → implementation → evidence

Authority: [capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md), [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md), [Day 5 rubric](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html). Track 2.

**Current revision: conversational English chat; live evidence pending.** No profile or form is required for search and opportunity questions. The 25-task suite includes the user's exact AI/Riyadh request, a city follow-up and requirements without academic inputs. The previous 20-task bilingual A/B results are historical and do not measure this source. The strict readiness checker intentionally rejects them for current submission.

| Requirement | Implementation | Actual evidence |
|---|---|---|
| Multi-step agent, ≥3 tools | Agent loop; four strict tools | Local tool/loop contracts pass; previous live traces are historical; fresh live evidence pending |
| ≥1 MCP tool | Search/details over separate stdio MCP process | Real SDK integration tests and live traces |
| Context file | `prompts/system.md`; one B instruction in `prompts/config_b.txt` | Loaded in each request; hashed in the manifest |
| Memory/retrieval | Empty normal session, last search, six complete conversation pairs, catalog retrieval; optional academic facts for eligibility only | Local follow-up/history integration plus three planned live multi-turn tasks |
| Compaction/context budget | Old complete pairs removed; tool-result cap; conservative input bound | Runtime tests and actual A token-budget stop |
| Permissions and approved write | Host-only one-use content-bound consent; recheck before SQLite commit | Local approval tests; current live approval cases pending; approval unit tests |
| Step/cost budgets | 8 model calls / 20 tools per request; token and cost checks; verified-free provider | Actual usage records and local budget tests; no paid fallback |
| ≥15 automatically graded tasks | 25 English tasks across 5 categories; course-standard fields and executable graders | `tasks.jsonl`, `evals/graders.py`; 50 current trials pending; previous 40 trials preserved as history |
| Two configurations evaluated | A base prompt; B one verification instruction; same model/runtime/data | New source-matched A/B run pending; do not reuse historical scores |
| Error analysis | Causal transcript review, paired flips and manually found grader gaps | `docs/error_analysis.md` marks the current analysis pending and links the previous analysis |
| Security note/trifecta | Private academic context, untrusted catalog text, model API egress | `SECURITY.md`, synthetic data and scoped tools |
| Attack and defence | Live injection observation plus independent forced-action authorization experiment | Current forced-action replay verifies consent; current live injection observation pending |
| Logs/operability | Usage, tool calls/results, approvals, stop reasons, bounded errors, explicit resume | Complete traces, retained quota interruption, current local test report |
| README/reproducibility | Problem, run instructions, ladder, tools, results, security, limits, diagram | README, `uv.lock`, Arabic walkthrough, scripted approval/denial demonstration |
| Synthetic/public data only | 30 fake opportunities and 6 fake profiles | Validated JSON fixtures; no real employer submission |
| No secrets in repository | `.env`/runtime excluded; key not forwarded to MCP | Repository secret scan; temporary local credential deleted after use |
| Repository/ZIP | Public GitHub repository; Download ZIP supported | Code and tasks current; historical CSVs/traces retained; fresh live evidence pending |
| Slides/presentation | Excluded per project owner's cohort instructions | Still present in the published rubric; no claim of changed grading weights |

## Evidence interpretation

The course does not require manufacturing a successful live model compromise. This project reports live resistance to the attempted injection and separately demonstrates the code guard stopping the requested malicious action. Live guard causality for that specific injection remains **unverified**, not silently inferred. Broader robustness needs more attacks and trials.

The read-only readiness checker and its own test changed after the full evaluation. Only `scripts/readiness.py` and `tests/test_readiness.py` are excluded from experiment-source compatibility; runtime, prompt, data, dependency, grader and evaluation-runner hashes must match. Original full manifests are preserved. Local verification requires exact current full hashes.

## Published rubric

| Criterion | Weight |
|---|---:|
| Working system/live demonstration | 25% |
| Context/harness engineering | 25% |
| Evaluation/error analysis | 20% |
| Security/governance/operability | 20% |
| Presentation/reproducibility | 10% |

Run `uv run python scripts/readiness.py --require-live`, and manually review actual results and cohort submission rules. The historical score of 100% on B's small automatic suite does not mean all its prose is correct or that academic acceptance is guaranteed.
