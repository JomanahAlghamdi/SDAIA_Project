# Requirement → implementation → evidence

Sources: [official capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md) and [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md). Track 2: Your harness. The owner also requested a simple HTML interface, public repository, and evaluator-owned API key.

Final machine-checked status is in [`results/requirements_status.json`](../results/requirements_status.json). Current live metrics and exact run references are in [`results/current_run_status.json`](../results/current_run_status.json). Historical scores never qualify as evidence for changed runtime, prompts, tools, data, graders or HTML files.

| Requirement | Implementation | Evidence |
|---|---|---|
| Multi-step agent with ≥3 tools | Four tools: search, details, eligibility, local draft | Actual model/tool traces; local contract tests |
| ≥1 tool over MCP | Search and details in a separate SDK stdio process | MCP handshake/integration tests and live tool traces |
| Context file | `prompts/system.md` and one additional B instruction | Loaded by the agent; source fingerprints in manifests |
| Memory/retrieval | Recent complete conversation pairs, previous filters, retrieved catalog records | Four multi-turn tasks, web city follow-up, context tests |
| Compaction/budget rule | Retire old complete pairs; cap tool output; measured-prefix reservation and actual-usage check | Nonzero-token regression and overshoot-before-action tests |
| Permissions and human-approved write | Exact preview; host-owned single-use consent; eligibility recheck | Approval/denial/duplicate tests and actual browser buttons |
| Step/cost limits | 8 model calls, 20 tools, 32,000 total tokens, 3,072 output tokens/call, $0.05 ceiling; reject positive reported cost | Effective limits, usage logs, cost guard tests; verified-free model |
| ≥15 automatically graded tasks | 25 English tasks, five categories, executable course graders | `tasks.jsonl`, A/B CSVs, transcripts and SQL assertions |
| Two configurations | Same model/runtime/data; B adds focused pre-recommendation eligibility verification | Complete current-source 25×2 experiment required |
| Error analysis | Transcript review, failed assertions, bidirectional A/B flips and historical regressions | `docs/error_analysis.md`; failures retained rather than rerun for a better score |
| Security note and trifecta | Optional private academic context, untrusted descriptions, model API egress | `SECURITY.md` |
| Attack and defence | OP030 injection; isolated live observation plus forced-action replay | Live model behavior reported separately from actual code-guard enforcement |
| Simple HTML UI (owner/cohort request) | Responsive English chat, suggestions, optional academic panel, explicit approval card | `web/`, `finder/web.py`, real browser screenshots/report and HTTP integration tests |
| Ordinary English conversation | Direct message; no profile required to browse | Exact AI/Riyadh request, requirements follow-up and city change |
| Public repository | `JomanahAlghamdi/SDAIA_Project`, visibility verified public | GitHub repository metadata |
| Evaluator supplies own key | Local `.env` read by Python; only blank `.env.example` submitted | No key sent to HTML/JavaScript; no tracked `.env` or detected key pattern in git history |
| Delete temporary test key last | Remove owner's GitHub Actions secret after validation; keep blank template | Cleanup status recorded separately; never claim deletion without confirmation |
| README/code/tasks/CSVs | Public repository and GitHub-generated ZIP; locked `uv` environment | README, run guide, `uv.lock`, current evidence and clean Windows/Linux CI |
| Slides/presentation | Excluded by the owner's prior cohort instructions | Still listed in the published rubric; exemption is not represented as a rubric change |

## Interpretation

The live browser check must complete the exact browsing flow, optional academic entry, denied write, approved write and duplicate prevention with a real model. A successful page load or scripted response alone does not satisfy that check.

The readiness check additionally requires the default B chat and consent/security demonstration cases to pass, a complete A/B experiment on one effective model, current security evidence and completed error analysis. Local verification must match exact current hashes. The two read-only evidence review files are excluded only from experiment-source comparison; all actual experiment inputs and web assets remain bound.

A resisted injection is not automatically evidence that the authorization guard caused resistance. The forced-action replay isolates that boundary; the live observation reports what the model actually attempted.

This is a technical evidence review, not a guarantee of a grade or of behavior on every possible question. One trial per task is not a repeated-reliability estimate. The data remain fictional and no employer submission exists.
