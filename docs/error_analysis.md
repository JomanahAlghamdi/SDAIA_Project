# Error analysis — current English chatbot revision

PENDING_LIVE_EVALUATION

The current source changes startup, language instructions, search interpretation and the task suite. It has no current live-model pass rate. Previous A=16/20 and B=20/20 results are preserved in [the historical analysis](history/2026-10-27/error_analysis.md), with the original traces under `results/live/20261027T202626-453723/`. They must not be relabeled as new results.

## New behavior to evaluate

- Direct English conversation without selecting a student or completing major/city menus.
- Exact request: "I need an internship opportunity for AI in Riyadh" must search field AI and city Riyadh without assuming an academic major or a training type.
- Browse candidates and their requirements without asking for GPA, year, registration or a profile.
- Retain AI on the follow-up "Are there any in Jeddah?"; do not silently change other preferences.
- Distinguish published requirements from verified personal eligibility. Optional formal checks/writes still require host-entered academic facts and independent exact-preview consent.
- Respond in English and report saved/denied/existing draft states accurately.

The suite contains 25 tasks (50 A/B trials). Automated checks cover script, IDs, filters, missing-information behavior and actions. They cannot prove naturalness, complete factual accuracy or the absence of all unnecessary questions. Manually inspect every new conversation, including passing ones.

Local integration uses a clearly scripted ReplayProvider with the real MCP subprocess. It establishes startup/input forwarding, follow-up context, session isolation and tool wiring, not real-model interpretation or accuracy. `results/local/verification.json` binds those checks to current source. Fresh A/B, live security and transcript review remain pending.

## Confirmed runtime defect from the user's screenshot (2026-10-28)

The screenshot shows two ordinary AI/Riyadh requests stopping with `token_budget`. The screenshot does not contain detailed usage logs, so its exact per-call consumption is unknown.

At source revision `9c0a3dd`, a deterministic regression with nonzero prompt counts 3,200 / 3,800 / 4,300 / 4,800 and 150 completion tokens per response reproduces the failure after three model responses and 11,750 cumulative tokens. The unused fourth scripted response would complete the answer. The old guard reserves the complete serialized byte length again, making a normal next request look unaffordable despite a 24,000 budget. Earlier `ReplayProvider` tests reported zero usage, hiding this failure.

The fix uses the previous measured prompt count only while both message prefix and tool schema are unchanged, plus a conservative allowance for appended messages. Changed prefixes/schemas or absent usage fall back to the full byte estimate. Actual usage still stops actions if the limit is exceeded. A new regression completes all four calls at 16,700 test tokens without raising the budget. Additional tests exercise changed prefixes, output reservation, history compaction, finite limits and visibility of a saved draft when a later answer fails.

No live success rate is inferred from this regression. The 25-task live suite now runs the three ordinary-chat scenarios first; the requirements scenario is a natural follow-up. The readiness checker requires current complete evidence, correct default demo behavior, a single effective A/B model, recorded limits, security evidence and human error analysis.

## First live review of ordinary chat (preserved, not the final revision)

Run `20261027T225952-462718` evaluated commit `c1ef6099d17637f3ed6ee10f9ed1136e6a3a4296`, on the unchanged 25 English tasks. A passed **17/25 (68%)** and B **19/25 (76%)**. All 50 trials completed without a provider interruption. The separate initial metadata failure is preserved as `20261027T225733-197704` (zero trials).

- The exact AI/Riyadh question now completed, but both configurations skipped detail retrieval and put unchecked candidate IDs in the eligible shortlist. B sometimes checked personal eligibility unnecessarily and requested academic fields during browsing. Follow-up city search filters were correct, but B included stale-city candidates in its prose. These are genuine workflow/contract defects; the task expectations are retained.
- Missing-kind, missing-duration and intake cases sometimes returned IDs despite unknown eligibility. Some correct prose still failed the structured shortlist contract. A final-response guard now asks the model to repair such an output; it does not silently rewrite the response or change the graders.
- A stopped on expired-deadline and forged-approval after repeated empty responses, each consuming the full 900 completion-token cap. The old trace did not record finish reasons/reasoning counts, so reasoning exhaustion is a hypothesis, not a measured fact for this run. OpenRouter documents that optional reasoning can consume the visible-output allowance. The new adapter disables optional reasoning when advertised, records finish reason/reasoning usage, and allows one response repair instead of repeatedly exhausting the budget.
- Manual review also found B's denied-save answer incorrectly asserted that no approval prompt was shown, although the host requested consent and recorded denial. The denial tool result now explicitly reports the observed approval request.
- No unauthorized draft was created in the protected live security observation. The live model also resisted the unsafe version, so this does not prove a causal improvement from the guard. The separate forced-action replay demonstrates blocked writes.

The instructions now distinguish browsing, personal assessment and local drafts, using empty shortlist/missing-info arrays for browsing and mandatory details retrieval. The same 24,000-token total and 900-token output limits remain. A fresh complete run is required because runtime and prompts changed.

Reference: [OpenRouter reasoning/output budget documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
