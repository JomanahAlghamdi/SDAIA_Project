# Run Internship Finder on Windows

## HTML interface (current)

After configuring `.env`, run `uv run python app.py web --as-of 2026-10-27` and open http://127.0.0.1:8000. Keep the terminal open. Type your question in English. Academic details are optional; a separate approval card controls local draft saving. The evaluator supplies their own key in `.env`. The key is never embedded in HTML/JavaScript or committed. This new interface is undergoing live browser/A-B verification; consult the final readiness report before submitting.


The current interface is English. Start by typing a normal English message. No profile or form is needed. Use fictional details for this synthetic coursework demo.

This revision still needs fresh live A/B and security evidence. Local tests and previous-version scores do not establish current submission readiness.

## 1. Open the project folder

Extract the ZIP. Open the inner folder containing `app.py`, `pyproject.toml` and `uv.lock`. Right-click empty space and choose **Open in Terminal**.

## 2. Install once

Run each line separately:

```powershell
uv --version
uv python install 3.12
uv sync --locked
```

If `uv` is not installed, follow the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/). A warning about standalone Python not being on PATH does not stop `uv run python`.

## 3. Configure the key locally

If `.env` is already configured, keep it. Otherwise:

```powershell
Copy-Item .env.example .env
notepad .env
```

Put your own key after `OPENROUTER_API_KEY=`. Leave the configured model value in place. Save and close. Never send this file/key to anyone or upload it to GitHub.

```powershell
uv run python app.py doctor
```

`key_present` and `model_configured` should be `true`. These check configuration presence; the real chat verifies provider access.

## 4. Start

```powershell
uv run python app.py chat --config B --as-of 2026-10-27
```

At `You:` type:

```text
I need an internship opportunity for AI in Riyadh
```

The assistant searches the fictional catalog and explains the options. It does not load `S001`, ask you to choose a major/city menu, or assume your major, GPA or year. The date flag is the demo catalog's reference date, not today's date.

## 5. Continue the conversation

```text
What are the requirements for OP012?
Are there any in Jeddah?
```

You can also ask about dates, duration, remote work or a different field. `/quit` exits; `/reset` starts a new conversation. `/help` lists optional commands. No personal record is needed for these questions.

For the separate approved-write course demo, you can run `uv run python app.py demo --interactive`. It uses explicitly fictional fixture data and scripted tool calls, not an LLM. Review its preview and type exactly `YES` to save the temporary local draft or `NO` to decline; nothing is sent to an employer.

To explore formal eligibility during real chat, `/details` optionally collects fictional academic facts; `/facts` shows them. This is needed only for the formal eligibility/draft demo, not browsing. A valid fixture example is AI, year 4, GPA 3.6/4, coop, 6 months, available 2027-01-01. After entering it, ask `Check OP001.` Then, if desired, `Prepare a local draft for OP001.` The separate exact-preview approval is still required.

## 6. Evaluation credentials on GitHub

A local `.env` is only on your computer. GitHub Actions needs its own encrypted repository secret:

1. Open repository **Settings → Secrets and variables → Actions**.
2. Create or update the repository secret named `OPENROUTER_API_KEY`.
3. Paste your key into the **Secret** field and save it. Do not put it in a repository file or workflow input.
4. Run **Live model evaluation (manual)** on the revision's branch, leaving `resume` empty for a new run. If a run stopped only because the secret was missing, its failed job can be rerun after adding the secret.
5. Inspect/download its evidence artifact. Commit the current results, review errors, and run the strict readiness check before submission.

## 7. Final checks

```powershell
uv run python scripts/verify_local.py
uv run python scripts/readiness.py --require-live
```

The second command deliberately fails until evidence matches the current code, tasks and prompts. Old bilingual results must not be presented as measurements of the new English chat.

## Token-budget fix and diagnosis

Use the current download; the previous English revision could stop on a simple AI/Riyadh request. The repaired reservation calculation works with the existing `IF_MAX_REQUEST_TOKENS=24000`; you do not need to raise it or replace your key. `doctor` now reports `budget_method: measured_prefix_plus_new_bytes` so you can identify the updated copy. If a request stops, the CLI shows its reason, request count and measured usage. Local draft outcomes are printed even if a later model answer fails.

The eval manifest records effective budgets; a resume refuses changed budgets. The ordinary-chat cases run first, including the user's exact message and a natural requirements follow-up. Finishing a run alone does not certify a working chatbot: default B's core demo cases must pass.
