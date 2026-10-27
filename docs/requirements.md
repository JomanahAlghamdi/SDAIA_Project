# Course requirement → implementation → evidence

Authority: [capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md), [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md), [Day 5 rubric](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html). Track 2.

The submitted technical evidence is complete. The final suite contains 20 tasks × 2 configurations, one trial each. A passed 16/20; B passed 20/20 on the automatic checks. Manual prose defects remain documented. [Machine checklist](../results/requirements_status.json) is not an academic grade or a universal accuracy guarantee.

| Requirement | Implementation | Actual evidence |
|---|---|---|
| Multi-step agent, ≥3 tools | Agent loop; four strict tools | Real-model search, eligibility and draft conversations in `results/live/20261027T202626-453723/traces` |
| ≥1 MCP tool | Search/details over separate stdio MCP process | Real SDK integration tests and live traces |
| Context file | `prompts/system.md`; one B instruction in `prompts/config_b.txt` | Loaded in each request; hashed in the manifest |
| Memory/retrieval | Scoped student profile, last search, six complete conversation pairs, catalog retrieval | Two multi-turn tasks passed for both configurations |
| Compaction/context budget | Old complete pairs removed; tool-result cap; conservative input bound | Runtime tests and actual A token-budget stop |
| Permissions and approved write | Host-only one-use content-bound consent; recheck before SQLite commit | Live approved/denied/duplicate tasks passed under both configurations; approval unit tests |
| Step/cost budgets | 8 model calls / 20 tools per request; token and cost checks; verified-free provider | Actual usage records and local budget tests; no paid fallback |
| ≥15 automatically graded tasks | 20 tasks across 5 categories; course-standard fields and executable graders | `tasks.jsonl`, `evals/graders.py`; 40 actual trials |
| Two configurations evaluated | A base prompt; B one verification instruction; same model/runtime/data | Complete manifest, 20 rows each in `eval_A.csv` / `eval_B.csv` |
| Error analysis | Causal transcript review, paired flips and manually found grader gaps | `docs/error_analysis.md`; four A failures and ungraded prose/language defects |
| Security note/trifecta | Private academic context, untrusted catalog text, model API egress | `SECURITY.md`, synthetic data and scoped tools |
| Attack and defence | Live injection observation plus independent forced-action authorization experiment | Live model resisted both variants; replay unsafe=1/defended=0; benign control succeeded; live denial cases also reached the guard |
| Logs/operability | Usage, tool calls/results, approvals, stop reasons, bounded errors, explicit resume | Complete traces, retained quota interruption, 87 passing local tests |
| README/reproducibility | Problem, run instructions, ladder, tools, results, security, limits, diagram | README, `uv.lock`, Arabic walkthrough, scripted approval/denial demonstration |
| Synthetic/public data only | 30 fake opportunities and 6 fake profiles | Validated JSON fixtures; no real employer submission |
| No secrets in repository | `.env`/runtime excluded; key not forwarded to MCP | Repository secret scan; temporary local credential deleted after use |
| Repository/ZIP | Public GitHub repository; Download ZIP supported | Code, tasks, CSVs, traces, security and documentation committed |
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

Run `uv run python scripts/readiness.py --require-live`, and manually review actual results and cohort submission rules. A score of 100% on B's small automatic suite does not mean all its prose is correct or that academic acceptance is guaranteed.
