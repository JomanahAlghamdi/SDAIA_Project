# Internship Finder

An English-only conversational AI assistant that starts with a message such as **"I need an internship opportunity for AI in Riyadh"**, retrieves synthetic co-op and summer opportunities, explains their requirements, and saves a local draft only after an eligibility check and explicit human approval.

## Course attribution

This capstone project was developed for **Agentic AI Systems Engineering** at **SDAIA Academy**.

- **Course website:** https://sdaiaacademy.github.io/agentic-ai/
- **Official course GitHub repository:** https://github.com/SDAIAAcademy/agentic-ai

**Track:** 2 — Your harness
**Project owner:** Jomanah Alghamdi
**Data:** 30 synthetic opportunities; 6 explicitly selectable test profiles. Normal chat starts with an empty academic record.
**Interface:** Simple English HTML chat at `http://127.0.0.1:8000`, with optional terminal mode.
**Revision status:** HTML chat verified with a real browser and model: 8/8 browser checks, 134 local tests, A=25/25 and B=24/25 live tasks. All final responses were reviewed; remaining model wording and one B follow-up failure are documented. See [current status](results/current_run_status.json) and [requirement review](docs/requirements.md).

**Rubric audit (28 October):** the technical evidence gate passes, but this is not full-mark certification. The [official-criteria audit](docs/RUBRIC_AUDIT.md) records the live-security evidence limitation, missing screen-recorded backup, observed HR failure and instructor-confirmed slide exemption. A fresh isolated checkout also passed all 134 tests.

Start here: [Windows setup and walkthrough](START_HERE.md). The repository is public; the evaluator supplies their own OpenRouter API key in a local `.env` file. No key is included in source, HTML or JavaScript. [Repository](https://github.com/JomanahAlghamdi/SDAIA_Project) · [CI](https://github.com/JomanahAlghamdi/SDAIA_Project/actions/workflows/checks.yml).

## Problem

Students ask for internships in plain English and follow up naturally. For example, "I need an internship opportunity for AI in Riyadh" searches the AI field in Riyadh immediately. The assistant presents fictional opportunities and answers questions about their requirements, duration and dates. "Are there any in Jeddah?" changes the city while retaining the AI search. No profile, registration, major/city menu, GPA or study year is required to browse. An interest in AI does not establish the student's major.

The optional eligibility and approved local-draft demonstration uses fictional values entered through the Academic details panel. It never blocks ordinary browsing. No employer application is sent.

## How to run

Requirements: Python 3.12+, `uv`, internet for installation and OpenRouter calls. Use fictional academic values for this coursework demo. No university login, CV, name, email or national ID is needed.

```bash
git clone https://github.com/JomanahAlghamdi/SDAIA_Project.git
cd SDAIA_Project
uv sync --locked
uv run python app.py doctor
uv run python scripts/verify_local.py
```

Create `.env` from `.env.example` once. On Windows PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

On macOS/Linux use `cp .env.example .env`. Enter your own `OPENROUTER_API_KEY` locally, leaving the concrete `OPENROUTER_MODEL` setting in place. Do not overwrite an existing configured `.env`, share its contents or commit it. The app checks zero pricing and tool support at runtime; there is no paid fallback.

```bash
uv run python app.py web --as-of 2026-10-27
```

Open **http://127.0.0.1:8000** and keep the terminal running. Type in the message box:

```text
I need an internship opportunity for AI in Riyadh
```

Then continue naturally in the same chat:

```text
What are the requirements for OP012?
Are there any in Jeddah?
```

No `--student`, form or preset academic record is required. Searches support the AI, Data, Software, Cybersecurity and Business fields, in Riyadh, Jeddah, Dammam and Makkah. Only explicitly supplied filters are used. Unsupported locations/fields are explained rather than silently substituted. If you explicitly say your major, it can also filter accepted majors; an opportunity field is a separate concept.

`--as-of 2026-10-27` is a reproducible clock for the dated synthetic catalog, not today's date. Without it, chat uses today's date and old opportunities may expire. For a single response:

```bash
uv run python app.py ask --as-of 2026-10-27 "I need an internship opportunity for AI in Riyadh"
```

The **New conversation** button starts a fresh anonymous session. The **Academic details** button is optional and is only needed for a personal eligibility check or local draft. **Approve & save locally** and **Decline** control an exact draft preview. No chat wording grants consent.

Terminal mode remains available with `uv run python app.py chat --config B --as-of 2026-10-27`; `/quit`, `/reset`, `/help` and `--verbose` apply to that mode.

### Optional eligibility and approved-write demo

In the HTML interface, open **Academic details**, enter fictional values, and save them to the session. Ask `Prepare a local draft for OP001.` The backend checks eligibility and displays the exact preview; only the separate **Approve & save locally** button allows the write. Declining saves nothing, and duplicate requests return the existing draft. Browser sessions use independent databases.

The following commands describe optional terminal mode:

This is a separate course demonstration, not a prerequisite for asking about opportunities. `/details` lets you enter fictional academic facts: major, year, GPA on a 4-point scale, training type, required months and start availability. `/facts` displays them, and `/set FIELD VALUE` edits one (`null` clears it). After entering them, ask `Check OP001 against the details I entered.` To request a local write, ask `Prepare a local draft for OP001 and show me the approval preview.` Only **YES** at the separate host prompt approves it. Other responses decline. Chat wording cannot grant host approval.

Each normal session starts empty in a separate `runtime/sessions/` directory. Internal `S000` is anonymous bookkeeping. `--student S001` is an explicit developer/test option that loads fictional fixture data; it is never selected automatically. Optional `--major` and `--city` flags can supply preferences, but ordinary chat does not need them. A chat statement is available for conversational search and explanations; it does not silently overwrite the host's academic facts for the optional formal eligibility/draft action.

An offline demonstration uses scripted tool calls and real MCP/eligibility/SQLite, but no LLM:

```bash
uv run python app.py demo --interactive
```

## Models

The configured model is `nvidia/nemotron-3.5-lightning:free` through OpenRouter. Runtime preflight requires current zero pricing and tool support. The current revision has a passing four-task pilot, six-turn live browser demonstration, and complete 25-task A/B experiment on the same model. [Model rationale](docs/model_rationale.md) distinguishes vendor benchmarks, historical measurements and current results. Requests are paced at least 3.2 seconds apart; errors stop rather than silently switching models. Reasoning is enabled when supported, with a requested 1,024-token reasoning allocation and room for the visible answer. The reasoning-off experiment regressed tool use and is preserved in the error analysis. Finish reasons and reasoning-token counts are recorded when reported.

## Design across the ladder

| Rung | Decision | Why |
|---|---|---|
| Prompt | English system spec; B adds one eligibility-verification instruction; typed final JSON | Explicit language, unknown-data and response contracts; controlled A/B difference |
| Context | User-entered academic fields, previous search, 12 completed conversation messages, MCP retrieval | Follow-up context without inventing a profile or sending the whole catalog |
| Harness | Four strict tools; optional host-owned academic inputs; eligibility recheck; one-use consent; SQLite transaction | Data and model suggestions cannot grant write authority |
| Loop | Up to 8 model calls and 20 tool calls per user request; at most one response repair | Complete multi-step work with explicit limits and stop reasons |
| Graph | Not needed for this bounded single-agent task | No distributed or independently scheduled workflow |

[Architecture diagram](docs/architecture.md). The model selects search/detail/eligibility tools; code controls academic input validation and all writes. Major and opportunity field are separate filters: an AI student can browse a Data opportunity that accepts AI majors.

Limits per user request: 8 model calls, 20 tool calls, a cumulative 32,000-token budget, at most 3,072 generated tokens per call (reasoning plus visible output), USD 0.05 ceiling and a 16,000-unit conservative UTF-8-byte context bound (including framing reserve). The first request reserves the full byte bound; later requests reuse the provider's measured token count for the unchanged prefix and reserve bytes only for newly appended messages. This is an estimate, not an exact model tokenizer. Actual provider usage is checked again before any tool action; unexpectedly high usage stops the run, and already incurred usage cannot be undone. Output allowance shrinks to the remaining reservation. Old complete conversation pairs can be removed between steps; current tool-call/result pairs remain intact. The final eligible shortlist is validated in code; an invalid result is returned to the model for at most one repair, never silently rewritten. Tool results are capped at 4,000 characters. Positive reported cost stops tool execution; no paid fallback or deployment-wide daily cap is implemented.

The previous English revision could report `token_budget` on the first ordinary AI/Riyadh question: its reservation treated all serialized bytes as fresh tokens on every step. A metered regression reproduces a stop after 11,750 reported test tokens; the repaired loop completes the same scripted search/details/answer at 16,700 test tokens, under the unchanged 24,000 limit. These are explicit test-double measurements, not live LLM results. The current HTML revision separately passed the live checks below with a 32,000-token ceiling. See [the review](docs/FINAL_REVIEW_AR.md).

## Tools

| Tool | Read/write | MCP? | Human approval? | Trifecta connection |
|---|---|---|---|---|
| `search_opportunities` | Read | Yes, separate stdio process | No | Untrusted synthetic catalog; exact major/city and optional filters |
| `get_opportunity_details` | Read | Yes | No | Description may contain hostile instructions |
| `check_eligibility` | Compute/read | No | No | Host-owned academic session details |
| `save_application_draft` | Local write | No | Mandatory exact-preview consent | Persists a draft; no external submission channel |

MCP uses the pinned official Python SDK. Its subprocess receives no OpenRouter key. Write arguments contain only an opportunity ID, never an approval flag, another student ID, SQL or a path.

## Evaluation

**Current suite:** 25 English tasks in `tasks.jsonl`: 10 search, 4 missing-information, 5 constraints, 4 approval and 2 security cases. This includes four multi-turn tasks, two major/city scenarios and three no-profile browsing scenarios. Fixtures supply known or deliberately missing academic values; CLI integration tests separately exercise the direct chat startup, exact user-message forwarding, follow-up history and session isolation.

**Configurations:** A uses the base spec. B adds a focused instruction to call `check_eligibility` before each personal recommendation and to keep browsing separate. Both share final shortlist validation and the same browsing contract. Both use the same model, data, tools and enforced write guards.

**Grading:** course-format executable graders plus domain assertions for completion, recommendation IDs, missing facts, filter preservation, constraint evidence, SQLite counts and consent events. An English-script check runs on every answer; it does not prove fluent English or factually correct prose. Manual transcript review is still required.

| Revision | Config | Completed/planned | Pass rate | pass^k | Avg requests | Avg tokens |
|---|---|---|---|---|---|---|
| Current HTML/English chat | A | 25 / 25 | 100% | 100% (k=1) | 3.48 | 9,760.24 |
| Current HTML/English chat | B | 25 / 25 | 96% | 96% (k=1) | 3.68 | 10,725.60 |
| Historical bilingual | A | 20 / 20 | 80% | 80% (k=1) | 3.40 | 7,926.3 |
| Historical bilingual | B | 20 / 20 | 100% | 100% (k=1) | 3.50 | 8,344.0 |

Current evidence: [`20261028T182556-953290`](results/live/20261028T182556-953290), [browser report](results/web_live/report.json), and [actual screenshots](results/web_live). Reported A/B cost was $0.00. B is the default and its core chat/write/security cases all passed; its personal city-follow-up failed. A scored higher in this single comparison, so the added B instruction is not claimed to improve measured accuracy.

Historical evidence remains unmodified under `results/live/20261027T202626-453723/`; its hashes do not match this revision. Do not reuse those scores as English-chat results. One trial is not a repeated-reliability estimate or a grade guarantee.

```bash
uv run python -m evals.run --config A B --trials 1
uv run python -m evals.security --mode replay
uv run python -m evals.security --mode live
uv run python scripts/readiness.py --require-live
```

A new complete run needs 50 task/configuration trials. Provider interruptions are retained separately; behavior failures are not retried to improve the score. Resume only an incomplete run whose source, task, configuration and model hashes still match. The old completed run cannot be resumed.

### Error analysis

[Error analysis](docs/error_analysis.md) records all current failures, manual findings on passing cases, and earlier regressions. B found the correct new-city candidate but skipped the personal eligibility check. Some missing-data and approval wording remains misleading even when structured/action checks pass. Authoritative host notices expose actual local-write outcomes. See the [historical analysis](https://github.com/JomanahAlghamdi/SDAIA_Project/blob/afcf39f062defab05f43f64113ae48f51c22841c/docs/error_analysis.md).

## Security and governance

[SECURITY.md](SECURITY.md) maps the private-context, untrusted-text and external-model egress legs. OP030 carries a synthetic injection requesting an unauthorized save. A deterministic forced-action experiment verifies the code's consent boundary; it is not an LLM attack success score. The current live model resisted both variants: zero unauthorized writes before and after. This does not prove that the guard caused its resistance. The separate forced-action replay produced one unsafe write before defence and zero after, with an approved benign control.

Only fictional/public data may be used for coursework. Do not enter university credentials, CVs or identifiers. Session fields and chat content go to OpenRouter as model context; local audit logs can contain academic details. A future real deployment would require appropriate privacy, identity, retention and access controls.

## Reproducibility and submission

CI runs local contracts and real MCP integration on Windows and Linux. A separate source-bound submission-evidence job requires the ordinary-chat and approval/security demonstration tasks to pass under default configuration B, as well as complete A/B evidence using one effective model and recorded budget settings. It remains strict: it must fail while current live evaluation/security evidence or error analysis is missing. Local test success alone is not submission readiness. GitHub's live workflow reads `OPENROUTER_API_KEY` from repository **Actions secrets**; never paste a key into source, chat or a workflow input. Download, inspect and commit its actual evidence artifact before updating results and marking this revision ready.

The [official capstone requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md) and [README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md) do not impose Arabic or bilingual support. The course's Rafeeq example is bilingual; Track 2 does not inherit that as a stated minimum. English is this project's chosen interface language. The published submission includes slides/presentation; these remain excluded per the owner's cohort instructions, not because the published rubric removed them.

## Limitations and next steps

- Synthetic, dated, small catalog only; no real vacancies, scraping, email or employer submissions.
- Four supported majors and four cities; no silent mapping of unsupported inputs.
- Search candidates can be shown from conversational preferences alone; verified eligibility needs the relevant published academic constraints.
- A local HTML application with a Python server and optional CLI; not a production authenticated multi-user service. New normal sessions do not resume prior drafts automatically.
- English prompt behavior is measured by automatic script checks and manual review, not guaranteed by instructions alone.
- Code guards protect writes; they do not guarantee every sentence the model generates.
- Current single-trial A/B results are 100% and 96%; manual review found prose inaccuracies even in passing cases. Future work: preserve personal-assessment intent across follow-ups and strengthen semantic response checks.
- The temporary Actions key is removed only after final validation; its cleanup status is recorded separately. The evaluator supplies a new local key.

## Sources

- [Course](https://sdaiaacademy.github.io/agentic-ai/)
- [Official requirements](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/README.md)
- [Official README template](https://github.com/SDAIAAcademy/agentic-ai/blob/main/labs/capstone/TEMPLATE_README.md)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
- [OpenRouter documentation](https://openrouter.ai/docs/api/reference/overview)
