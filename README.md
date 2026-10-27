# Internship Finder

An Arabic/English agent that helps university students find suitable synthetic co-op and summer opportunities, checks published requirements, and saves a local application draft only after human approval.

**Track:** 2 — Your harness  
**Project owner:** Jomanah Alghamdi  
**Data:** 30 synthetic opportunities, 6 synthetic student profiles; no real vacancies or employers.  
**Status:** Implementation and local contract/MCP/security checks available. **Live model evaluation A/B, live prompt-injection evidence and final root-cause analysis are pending an OpenRouter key and a selected model. This is not yet a verified final capstone submission.**

Start in Arabic: [START_HERE_AR.md](START_HERE_AR.md). Exact requirement evidence: [docs/requirements.md](docs/requirements.md).

Repository: [JomanahAlghamdi/SDAIA_Project](https://github.com/JomanahAlghamdi/SDAIA_Project). [Local CI](https://github.com/JomanahAlghamdi/SDAIA_Project/actions/workflows/checks.yml) runs tests, real MCP connectivity and the security replay on every push. A green local CI result does not establish live model evaluation readiness.

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

For one repeatable local evidence run (tests + MCP + security replay + syntax checks), use `uv run python scripts/verify_local.py`. It records source hashes so readiness cannot reuse stale local evidence after code changes.

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

The runtime uses OpenRouter Chat Completions with a **single explicitly selected, currently free tool-calling model**. `.env.example` suggests `google/gemma-4-31b-it:free`, matching the course's starting model and confirmed in OpenRouter's free tool-calling list on 2026-10-27 (see `docs/model_candidate.json`). This is a provisional feasibility choice, not a performance finding. `app.py models` obtains current metadata; the runtime verifies availability and zero pricing again. Before submission, record public tool-use benchmark evidence if available, exact effective model IDs, and the project's actual A/B scores. Those quality comparisons are **not yet measured**. Model substitution is explicit; both configurations must be rerun after substitution.

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

| Config | Live pass rate | pass^k | Avg requests | Avg tokens |
|---|---|---|---|---|
| A | Not run — key/model required | Not measured | Not measured | Not measured |
| B | Not run — key/model required | Not measured | Not measured | Not measured |

Local unit/integration results in `results/local/` are **not** model evaluation scores. No live `eval_A.csv` or `eval_B.csv` is fabricated. Running the suite produces separate CSVs, a version/hash manifest, per-task transcripts and `summary.md` under a new `results/live/<run>/` directory. `pass^k` is the fraction of tasks that passed **every observed trial**; k=1 does not establish repeated reliability. Provider caching/temperature can still affect independence; no statistical significance claim is made.

### Error analysis

Pending live execution. The runner counts failed assertions and shows A→B flips in both directions. These are failure signals, **not inferred root causes**. Read the transcripts and complete [docs/error_analysis.md](docs/error_analysis.md) with causal explanations, counts, example IDs and fixes. Never invent an improvement to satisfy the rubric.

## Security note

See [SECURITY.md](SECURITY.md) for the trifecta, injected fixture, code defence, before/after contract replay, live experiment procedure, privacy boundary and residual risks. `results/security_replay/report.json` demonstrates that a worst-case malicious tool call can write in the deliberately unsafe test variant, is blocked by the protected variant, and legitimate approved writes still succeed. It is explicitly **not an LLM prompt-injection success measurement**. The live experiment is pending credentials.

## Reproducibility and submission

1. Clone/extract into a clean directory; run `uv sync --locked`, tests and `doctor`.
2. Configure a local key and explicit model; run the conversational demo with a real human approval.
3. Run both live configurations on all 20 tasks; save actual CSVs/transcripts and inspect failures.
4. Run the live security experiment and honestly report whether the attack worked before the defence.
5. Finish model rationale and root-cause analysis; update the README table from actual results.
6. Run `uv run python scripts/readiness.py --require-live`; review the requirement matrix.
7. Submit a shared/public repository or ZIP; never include `.env`, keys, `.venv` or private data.

Automatic GitHub CI runs local contracts only. The separate live workflow requires an `OPENROUTER_API_KEY` repository secret. It can be manually dispatched with an explicit model ID, or triggered by committing a change to `.github/live-eval-request.json` after the secret is configured (the push trigger uses the concrete model ID specified in the workflow). Both paths revalidate that the model is free and supports tools. Each live run uploads its evidence as a GitHub Actions artifact; inspect the results and commit the completed CSVs, traces and analysis before submission. No live GitHub run is claimed yet.

The course's published submission also includes slides/a live presentation. The project owner stated that their cohort does not require a presentation, so no slides are included. No change to the published grading weights is assumed.

## Limitations and next steps

- Synthetic, dated catalog only; no real vacancies, scraping, email or application submission.
- CLI demonstration, not a hosted website or authenticated multi-user service. Student selection is trusted local input; it is not real identity verification.
- Human approval applies to local draft storage only, not employer/university approval.
- Session memory is in-process and resets on restart; drafts persist in local SQLite for live chat.
- Matching enforces only modeled, published requirements. Unknown GPA/date/major fields remain unknown.
- Exact domain labels/filters, a small catalog, limited attack coverage and simple automatic graders.
- No operational deployment or verified live model performance yet. Larger data, robust authentication, retention policies and expanded evaluation are future work.

## Sources

- [Course page](https://sdaiaacademy.github.io/agentic-ai/)
- [Official capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md)
- [Official README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md)
- [Day 5 rubric](https://sdaiaacademy.github.io/agentic-ai/slides/day5.html)
- [Official MCP Python SDK v1 documentation](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
- [OpenRouter API documentation](https://openrouter.ai/docs/api/reference/overview)
