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
