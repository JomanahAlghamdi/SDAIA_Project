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
