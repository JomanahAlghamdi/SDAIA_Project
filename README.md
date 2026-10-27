# Internship Finder

An Arabic/English agent that helps university students find suitable synthetic co-op and summer opportunities, checks published requirements, and saves a local application draft only after human approval.

**Track:** 2 — Your harness  
**Project owner:** Jomanah Alghamdi  
**Data:** 30 synthetic opportunities, 6 synthetic student profiles; no real vacancies or employers.  
**Status:** Technical submission evidence is complete: **87 local tests pass; all 20 tasks ran on A and B (40 trials). A passed 16/20 (80%); B passed 20/20 (100%) on the automatic graders.** Manual transcript review found wording/language defects that these graders miss; see the error analysis. The live injection was resisted in both variants. A separate forced-action experiment proves the approval guard, and live A/B approval-denial tests also reached that guard. This is a measured course prototype, not a promise of perfect answers or academic acceptance.

Start in Arabic: [START_HERE_AR.md](START_HERE_AR.md). Exact requirement evidence: [docs/requirements.md](docs/requirements.md).

Step-by-step Arabic instructions for GitHub evaluation, Windows execution and handing in the repository: [SUBMISSION_AR.md](SUBMISSION_AR.md).

Repository: [JomanahAlghamdi/SDAIA_Project](https://github.com/JomanahAlghamdi/SDAIA_Project). [Local CI](https://github.com/JomanahAlghamdi/SDAIA_Project/actions/workflows/checks.yml) runs tests, real MCP connectivity and the security replay on every push. A green local CI result does not establish live model evaluation readiness.

Detailed Arabic submission review: [docs/FINAL_REVIEW_AR.md](docs/FINAL_REVIEW_AR.md).

## Problem

Students need to compare placements across training type, specialization, city, attendance mode, duration and start dates. A vacancy that sounds relevant can still fail academic requirements or have an expired deadline. Internship Finder accepts a conversational request, retrieves candidates, inspects details and checks eligibility in code. It explains known mismatches and unknown information. The student can then review a local draft and explicitly approve saving it. A task is complete when the assistant returns grounded options or an honest no-match response, and an optional draft is saved only after approval. No application is sent to an employer.

## How to run

Requirements: Python 3.12 or newer, [uv](https://docs.astral.sh/uv/getting-started/installation/), internet for dependency installation and live model calls. The local tests/demo do not call a model.

From the repository root:

```bash
git clone https://github.com/JomanahAlghamdi/SDAIA_Project.git
cd SDAIA_Project
uv sync --locked
uv run python app.py doctor
uv run pytest -q
uv run python app.py demo --interactive
```

For one repeatable local evidence run (tests + MCP + security replay + syntax checks), use `uv run python scripts/verify_local.py`. It records full source hashes so readiness cannot reuse stale local test evidence after code changes.

The demo uses **scripted tool calls**, a real MCP subprocess, real eligibility rules and a disposable SQLite database. It does not understand arbitrary language or measure model quality. Omitting `--interactive` denies the requested write.

For the real conversational agent:

```bash
cp .env.example .env
uv run python app.py models
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp`. Edit `.env` locally: fill `OPENROUTER_API_KEY` and choose one concrete free tool-calling `OPENROUTER_MODEL` returned by the models command. Never commit or share the key. The app verifies zero pricing and tool support before starting; it fails closed if metadata is unavailable. No paid fallback is enabled.

```bash
uv run python app.py chat --student S001 --config B --as-of 2026-10-27
uv run python app.py ask --student S001 --as-of 2026-10-27 "Find a Data co-op in Riyadh that fits my profile."
```

`--as-of` makes the dated synthetic fixture reproducible. Normal chat without this flag uses today's date; old fixtures eventually expire.

In chat: `/profile` shows the trusted profile; `/set FIELD VALUE` updates it from direct user input; `/reset` clears conversation memory; `/quit` exits. Example: `/set available_from 2027-01-01`. Editable fields are `major`, `year`, `gpa`, `training_kind`, `required_months`, `available_from`; `null` represents missing information. GPA uses a 4-point scale. `training_kind` is `coop` or `summer`. Profiles cannot be edited by an LLM tool.

```bash
uv run python -m evals.run --config A B --trials 1
uv run python -m evals.security --mode replay
uv run python -m evals.security --mode live
uv run python scripts/readiness.py
```

For repeated reliability, rerun the full live suite with `--trials 3` when quota allows. That is 120 task runs (20 × 2 × 3), often multiple model requests each. No fixed quota entitlement is assumed. Provider failure stops the evaluation with an incomplete manifest; partial CSVs must not be reported as a complete suite.

## Models and provider choice

The current model is **`nvidia/nemotron-3.5-lightning:free`**, selected explicitly after both Gemma candidates returned upstream-capacity HTTP 429 errors. A real pilot verified tool use at zero reported cost. The runtime checks current zero pricing and tool support before each session; there is no paid fallback. Model metadata is in `docs/model_candidate.json`; vendor benchmark evidence, the availability tradeoff and Arabic-language limitations are documented in [docs/model_rationale.md](docs/model_rationale.md). A pilot or vendor benchmark does not replace this project's A/B evaluation. Both configurations use the same concrete model.

The provider paces requests at least 3.2 seconds apart. Free-account quota may require multiple sessions. Resume an incomplete v2 evaluation explicitly with:

```bash
uv run python -m evals.run --config A B --trials 1 --resume results/live/<run>
```

Resume validates the source/task hashes, model and configurations. Completed task trials, including behavioral failures, are retained. Infrastructure interruptions remain recorded separately and only the interrupted or unstarted trials are executed again. No partial suite is presented as complete.

## Design across the ladder

| Rung | Decision | Why |
|---|---|---|
| Prompt | Loaded `prompts/system.md`; B adds only `prompts/config_b.txt`; typed tool schemas and final JSON | Clear contract; controlled A/B change; exact IDs for grading |
| Context | Structured session profile, last search filters, last 12 completed user/assistant messages, MCP retrieval | Follow-ups retain context without sending the entire catalog |
| Harness | Four-tool allowlist, strict schemas, host-only approval, eligibility recheck, SQLite transaction, logs and budgets | Untrusted descriptions cannot grant authority |
| Loop | Up to 8 model calls and 20 tool calls per request, recoverable tool errors, bounded output repair | Multi-step tasks with explicit stop reasons |
| Graph | Not required for this scope; a single agent loop owns tool dispatch | No independent agents or distributed long-running workflow to coordinate |

The model chooses search/inspection actions and asks clarifying questions; deterministic code owns eligibility and writes. [Architecture diagram](docs/architecture.md).

### Context and operational budgets

Defaults: 8 model calls, 20 tool calls, 24,000 actual total tokens per user request, 900 maximum output tokens per call and USD 0.05 cost ceiling. Each prompt also has a conservative 16,000-token **upper-bound estimate using UTF-8 bytes plus framing**, not a measured tokenizer count. Old complete conversation pairs are dropped first. Tool results are capped at 4,000 characters with an explicit truncation marker. Persistent profile/filter state and the current tool exchanges are preserved; approval is never held in model context.

Actual provider usage is logged separately. Preflight token checks are deliberately conservative. Only zero-price models are accepted, including a per-request provider max-price restriction; positive reported cost triggers a stop before tool execution. The application cannot undo provider charges already reported. Missing/malformed usage fails closed. Limits reset per user request; this prototype does **not** provide a deployment-wide daily spend cap. Requests are sequential, with bounded HTTP timeout; failures are reported, not silently retried or rerouted.

## Tools

| Tool | Read/write | MCP? | Approval? | Risk relationship |
|---|---|---|---|---|
| `search_opportunities` | Read | Yes, stdio | No | Retrieves synthetic, potentially untrusted catalog facts |
| `get_opportunity_details` | Read | Yes, stdio | No | Description can contain hostile text |
| `check_eligibility` | Read/compute | No | No | Uses current student's scoped profile |
| `save_application_draft` | Write locally | No | Mandatory human host callback | Persists a draft; no external recipient/channel |

`mcp_server.py` runs in a separate process using the official Python MCP SDK, pinned by `uv.lock`. Version 1.x is intentionally pinned for the stable FastMCP client/server API; the actual negotiated protocol is printed by `doctor`. The capstone minimum requires an MCP tool; it does not mandate the course lab's SDK major version. The subprocess receives no OpenRouter credentials. The write tool accepts only an opportunity ID; it cannot accept an approval flag, student ID or arbitrary SQL/path.

## Evaluation

**Suite:** 20 tasks in `tasks.jsonl`: 6 search, 4 missing information, 5 constraints, 3 approvals, 2 security. Arabic and English tasks, including two multi-turn cases. Each task has explicit expected outputs and allowed simulated human decisions. Each configuration/trial uses a fresh database and memory. Evaluation time is fixed to 2026-10-27; provider calls are fresh with no application response cache. A/B executions are interleaved within tasks to reduce order confounds.

**Configurations:** A = base system instructions; B = the same instructions plus one instruction requiring an eligibility tool call before recommending suitability. Same tools, permissions, guards, data and selected model. The extra instruction does not weaken A's write controls.

**Graders:** completion/JSON validity, exact allowed recommendation IDs, required tool calls, missing-field requests, search-filter preservation, eligibility failure evidence, SQLite draft counts and approval trace events. These graders measure selected behaviors; they do not exhaustively verify all prose or every possible attack. Inspect transcripts manually for explanation quality, false claims and root causes.

Every task includes the course-standard `id`, `category`, `lang`, `prompt` and `graders` fields. The runner executes deterministic course `db` and `tool_called` graders, plus the stricter domain assertions in `expect`. It also supports `contains_any`, `not_contains` and `tool_not_called`. Database graders use read-only SQLite authorization. `turns` extends the format for follow-up tests; `prompt` is always the first turn. Use this repository's runner to preserve the synthetic profile, approval simulation and multi-turn state.

**Complete live evidence:** [run manifest](results/live/20261027T202626-453723/manifest.json), [A CSV](results/live/20261027T202626-453723/eval_A.csv), [B CSV](results/live/20261027T202626-453723/eval_B.csv), [summary](results/live/20261027T202626-453723/summary.md).

| Config | Finished / planned | Pass rate | pass^k (k=1) | Avg requests | Avg tokens |
|---|---:|---:|---:|---:|---:|
| A | 20 / 20 | 16/20 (80%) | 80% | 3.40 | 7,926.3 |
| B | 20 / 20 | 20/20 (100%) | 100% | 3.50 | 8,344.0 |

Four A-fail/B-pass flips and no reverse flip were observed. With one trial per task/configuration, this is not a statistical or causal improvement claim. The account quota interrupted B's city-change task; after quota was raised, the unfinished trials resumed with identical experiment source, prompts, tasks and model. The interrupted attempt remains in the manifest and trace, outside the completed-trial denominator. All 40 completed rows reported USD 0 cost. The original 11-row partial summary is retained as historical evidence only.

Local unit/integration results in `results/local/` are **not** model evaluation scores. Running the suite produces real CSVs, a version/hash manifest and per-task transcripts under `results/live/<run>/`; `summary.md` is produced only on completion. `pass^k` is the fraction of tasks that passed **every observed trial**; k=1 does not establish repeated reliability. Provider caching/temperature can still affect independence; no statistical significance claim is made.

### Error analysis

One A failure returned prose instead of final JSON and exhausted the conservative repair budget. Three A failures put an opportunity ID in the recommendation field while also requesting missing profile information. B passed these checks, but manual review still found misleading approval/submission wording and two Arabic tasks answered in English. These are real limitations outside the current automatic assertions, not grounds for claiming perfect B behavior. [Full root-cause analysis](docs/error_analysis.md) separates the four graded failures, ungraded prose defects and provider interruption.

## Security note

See [SECURITY.md](SECURITY.md) for the trifecta, injected fixture, code defence, before/after contract replay, live experiment procedure, privacy boundary and residual risks. `results/security_replay/report.json` demonstrates that a worst-case malicious tool call can write in the deliberately unsafe test variant, is blocked by the protected variant, and legitimate approved writes still succeed. It is explicitly **not an LLM prompt-injection success measurement**. The completed live experiment resisted the injection in both variants; only the separate forced-action replay reached and demonstrated the approval guard.

## Reproducibility and submission

1. Clone/extract into a clean directory; run `uv sync --locked`, tests and `doctor`.
2. Configure a local key and explicit model; run the conversational demo with a real human approval.
3. Run both live configurations on all 20 tasks; save actual CSVs/transcripts and inspect failures.
4. Run the live security experiment and honestly report whether the attack worked before the defence.
5. Finish model rationale and root-cause analysis; update the README table from actual results.
6. Run `uv run python scripts/readiness.py --require-live`; review the requirement matrix.
7. Submit a shared/public repository or ZIP; never include `.env`, keys, `.venv` or private data.

Automatic GitHub CI runs local contracts only. The separate live workflow requires an `OPENROUTER_API_KEY` repository secret for future runs. Manually dispatch it with the default model and an empty `resume` field for a new evaluation. The completed run cannot be resumed. The push-trigger request file is historical; update it only for an intentional new run, with a valid incomplete run path or no resume field. Both paths revalidate zero pricing and tool support. Each run uploads an evidence artifact; inspect and commit new results before changing the published scores. The submitted real-model evidence was executed locally; earlier GitHub attempts stopped before model calls because the repository secret was missing.

The readiness checker now reports three separate facts: live attack observation, forced-action guard enforcement, and live guard causality. The last remains false when the model resists before reaching the guard. Course evidence is checked using the completed live observation plus the independently verified guard experiment, not a requirement to make the model vulnerable. Original experiment manifests retain all hashes. Only the read-only readiness checker and its own tests are excluded when comparing experiment source; every runtime, prompt, data, dependency, grader and evaluation-runner hash must still match. The checker change did not alter agent behavior or A/B grading. Local verification always requires exact current full hashes.

The course's published submission also includes slides/a live presentation. The project owner stated that their cohort does not require a presentation, so no slides are included. No change to the published grading weights is assumed.

## Limitations and next steps

- Synthetic, dated catalog only; no real vacancies, scraping, email or application submission.
- CLI demonstration, not a hosted website or authenticated multi-user service. Student selection is trusted local input; it is not real identity verification.
- Human approval applies to local draft storage only, not employer/university approval.
- Session memory is in-process and resets on restart; drafts persist in local SQLite for live chat.
- Matching enforces only modeled, published requirements. Unknown GPA/date/major fields remain unknown.
- Exact domain labels/filters, a small catalog, limited attack coverage and simple automatic graders.
- One observed trial on a small synthetic suite; automatic graders do not exhaustively verify language or claims. Some passing transcripts inaccurately describe future employer submission or pending approval; the host always states that drafts stay local, and no external submission tool exists. Larger data, stronger answer validation, authentication and repeated evaluation are future work.

## Sources

- [Course page](https://sdaiaacademy.github.io/agentic-ai/)
- [Official capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md)
- [Official README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md)
- [Day 5 rubric](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html)
- [Official MCP Python SDK v1 documentation](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
- [OpenRouter API documentation](https://openrouter.ai/docs/api/reference/overview)
