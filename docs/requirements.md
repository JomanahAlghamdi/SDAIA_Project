# Course requirement → implementation → evidence

Authority: [official capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md), [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md), [Day 5 scoring guide](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html). Reviewed 2026-10-27. The project follows Track 2.

“Implemented” describes source code. “Verified locally” describes actual non-LLM tests. Neither label substitutes for the required live A/B evaluation.

| Requirement | Implementation | Evidence/status |
|---|---|---|
| Multi-step agent, ≥3 tools | `finder/agent.py`, four strict tools in `finder/models.py` | Scripted end-to-end four-tool integration tested; actual LLM task completion pending key/model |
| ≥1 exposed/consumed MCP tool | Search and details via separate `mcp_server.py`, `finder/mcp_client.py` | Real SDK initialization/list/call tests; `app.py doctor` |
| Context file | `prompts/system.md` loaded per run; B extra instruction separate | Runtime and manifest hashes; no unused spec file |
| Memory or retrieval | Structured profile, last search and bounded conversation pairs; catalog retrieval | Runtime tests, multi-turn live tasks ready |
| Compaction or context budget | Last 12 messages (6 complete user/assistant pairs), cap on results, byte-based conservative token bound | `finder/agent.py`; budget/memory tests |
| Permission policy and human approval for a write | Read allowlist; exact-preview host callback; one-use content-bound approval; atomic SQLite commit | `tests/test_approvals.py`; interactive demo; no LLM-supplied approval field |
| Step and cost budgets | 8 model calls/20 tool calls; token/cost meters and pre/post checks; verified-free routing | Meter tests, explicit stop reasons; live metering awaiting provider |
| ≥15 eval tasks with automatic graders | 20 task objects; output/tool/constraint/DB/approval graders | `tasks.jsonl`, `evals/graders.py`; fixture coverage tests |
| Two configurations actually evaluated | A base prompt; B one added verification instruction; same data/tools/model | Runner implemented; **BLOCKED: no OpenRouter key/model. No actual live A/B CSVs yet.** |
| Error analysis | Runner counts failed assertions and A/B flips; manual causal analysis template | **PENDING** actual transcripts; `docs/error_analysis.md` |
| Security note/trifecta | Data boundaries, untrusted descriptions, model egress, minimization and oversight | `SECURITY.md` |
| Attack and defence | OP030 injection; isolated unsafe test variant versus approval gate | Authorization replay actually run, benign control preserved; **live LLM injection experiment pending** |
| Logs/traces and operability | Tool results, approvals, guard blocks, usage and stop reasons; clean failure paths | Actual local traces; provider/limit tests; no automatic paid fallback |
| README from template | Problem/run/design/tools/eval/security/limits sections; architecture diagram | `README.md`, `docs/architecture.md`; live scores/model rationale visibly pending |
| Runnable via uv + OpenRouter key | Pinned `pyproject.toml`/`uv.lock`, `.env.example`, CLI | Clean extraction/local tests; full real-model clean run pending key |
| Synthetic or public data only | 30 clearly labeled fake companies/opportunities, 6 fake academic profiles | `scripts/generate_data.py`, validated JSON fixtures |
| No secrets in repository | `.env` and runtime DB excluded; only `.env.example`; credentials not sent to MCP | Package content/secret scan; provider errors redact response bodies |
| Slides/presentation | Excluded per project owner's instruction | Published requirement remains; no claim that grading weights changed |

## Published rubric

| Criterion | Weight |
|---|---:|
| Working system/live demonstration | 25% |
| Context/harness engineering choices | 25% |
| Evaluation/error analysis | 20% |
| Security/governance/operability | 20% |
| Presentation/reproducibility | 10% |

Before submission, complete the **pending live evidence** and inspect all failures. Passing local tests is not a promise of model accuracy or course completion. Run `uv run python scripts/readiness.py` for machine-readable status.
