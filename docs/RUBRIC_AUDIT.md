# Official rubric audit — 28 October 2026

**Conclusion:** The source contains the technical components expected for Track 2, with actual live and local evidence. A full mark is not verified or predicted. The Day 5 strongest-evidence guide exposes gaps that the repository's narrower technical readiness gate does not certify. This review keeps original scores and failed responses unchanged.

Reviewed repository: `JomanahAlghamdi/SDAIA_Project`, public, commit `48d3173fa29b3c2f2acf88d5209ee6a694ea14b2`. Runtime evidence is bound to the code introduced at `0c7ca0d7`; subsequent docs/results commits do not change its inputs. [Machine-readable review and fresh local results](../results/audit/2026-10-28/).

## Authoritative sources and scope

- [Program page](https://sdaiaacademy.github.io/agentic-ai/) — tracks and rubric.
- [Capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md) — minimums, submission and preparation.
- [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md) — requested evidence structure, including counted root causes.
- [Day 5 scoring guide](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html) — what strongest evidence looks like.

The official capstone says “Use synthetic or public data only.” The fictional opportunity catalog satisfies that data-type rule. The published Track 2 requirements do not impose Arabic or bilingual support; English-only is consistent with those documents. This is an inference from the absence of a language requirement, not a quotation explicitly granting an English-only exemption. Rafeeq's bilingual case study is not automatically a Track 2 requirement.

The owner reconfirmed on 28 October that slides are exempt by the instructor. That cohort direction is respected. The public rubric still lists presentation; the exemption is not falsely attributed to the published document. HTML, a public repo, evaluator-owned key, and final removal of the temporary testing key are additional owner/cohort instructions.

## Criterion-by-criterion evidence

| Official criterion | Weight | Verified implementation/evidence | Remaining limit |
|---|---:|---|---|
| Working system and live demo | 25% | English HTML; four tools; real MCP; exact AI/Riyadh, requirements and Jeddah browser conversation; approval/denial/duplicate paths | One B personal-follow-up failure; owner screenshot shows a failed `for hr` turn; timing/prose errors remain. Recorded finite tests do not cover every request. |
| Context and harness decisions | 25% | System spec; limited complete-turn memory; catalog retrieval; compaction/result limits; step/token/cost controls; host approval and transaction-bound writes; architecture and rationale | No claim that every course topic (graphs, multi-agent, three API shapes) is required or implemented. This bounded Track 2 project explains why a graph is unnecessary. |
| Evaluation and error analysis | 20% | 25 tasks on A/B, same concrete model; original CSVs and transcripts; 25/25 A and 24/25 B; paired flips; root-cause count table now added | One trial per task; not repeated reliability. B did not outperform A. Prose defects missed by graders are separately counted. |
| Security, governance, operability | 20% | Trifecta mapping; strict write schema; one-use consent; isolated attack; deterministic forced-action before/after 1→0 drafts; approved benign control; actual live observation; logs; minimization/residency limits documented | Actual model resisted both original attack variants (0→0). This does not establish the successful-before/blocked-after live injection asked for as strongest evidence. No causal claim is made for a guard the model never reached. |
| Presentation and reproducibility | 10% | Instructor-confirmed slide exemption; complete run guide; locked dependencies; public repo; Windows/Linux CI; clean source checkout/new environment passes 134 tests | A real screen-recorded backup is absent. Existing PNGs and transcripts are not a two-minute video. Live delivery/Q&A cannot be scored in advance. |

The minimum counts are exceeded: four tools including two MCP tools, and 25 tasks per configuration. The scope of the security demonstration must remain explicit. The grader is allowed to value a transparent failed attack, but this audit cannot assume that yields full marks on the stronger guide.

## Fresh reproducibility check

The verified remote HEAD was exported through `git archive` into a new directory, without `.env`, runtime databases or an existing virtual environment. `uv sync --python 3.12 --locked` created a fresh environment. Local contracts (134), actual MCP integration, doctor, replay-security control, compilation and source-bound readiness passed. This is an isolated clean source checkout, not a claimed second network clone or a new live LLM measurement.

[CI run 40749204926](https://github.com/JomanahAlghamdi/SDAIA_Project/actions/runs/40749204926) separately passed Ubuntu, Windows and submission-evidence jobs. The public code and reachable Git history were scanned for common OpenRouter/GitHub key patterns; no matches and no tracked `.env` were found. This is a limited pattern scan, not proof that all possible secrets are absent. Removal of the Actions secret is still unverified.

## Corrections made during this audit

1. Replaced stale `START_HERE_AR.md`: it incorrectly cited 87 tests and the historical 20-task scores, started with a preset profile, and used Arabic sample prompts. It now points to the current English HTML flow and actual 134/25-task results.
2. Added counted root causes and manual findings to `docs/error_analysis.md`, without changing any original grader output.
3. Clarified that a green technical readiness check is not full-rubric certification.
4. Recorded the renewed instructor exemption for slides and the unresolved key-cleanup status.
5. Added fresh clean-checkout evidence. No runtime, prompt, tool, grader, task or dependency was changed during this audit; existing live evidence remains applicable.

## Open work before claiming complete strongest-evidence coverage

- Reproduce the owner's short `for hr` sequence with its actual audit log; diagnose the recorded stop reason, add a regression, and remeasure if runtime or prompts change. HR is outside the current catalog, so a clear scope explanation is appropriate. A generic failure is not a successful unsupported-domain response.
- Correct and remeasure personal-assessment follow-up intent and inaccurate missing-data/approval wording. Do not silently swap to A or rerun only a failed trial to inflate the original B score.
- If pursuing the strongest live-security demonstration, use a clearly isolated vulnerable test baseline and preserved attacker inputs, with real model traces before and after. Keep the current resisted attack and separate replay; do not fabricate success or weaken the deployed authorization boundary.
- Record a real short browser demo as a fallback, including a multi-step task and approval. Screenshots or a scripted model are not substitutes for a claimed live recording.
- After final testing, remove the temporary Actions key and verify its absence. Keep the blank `.env.example` so the evaluator can configure their own key.

None of these points makes synthetic data or English a violation. They identify evidence and behavior limits relevant to the actual scoring guide.
