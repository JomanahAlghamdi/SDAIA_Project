# Open the English HTML assistant on Windows

## 1. Get the project

Download the public repository using **Code → Download ZIP**, extract it, and open the inner folder containing `app.py`, `pyproject.toml` and `uv.lock`. Open PowerShell in that folder.

## 2. Install dependencies

```powershell
uv python install 3.12
uv sync --python 3.12 --locked
```

If `uv` is missing, use the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

## 3. Supply your own API key

The evaluator supplies their own OpenRouter key. The repository contains only an empty `.env.example` template. If `.env` does not already exist:

```powershell
Copy-Item .env.example .env
notepad .env
```

Enter the key after `OPENROUTER_API_KEY=` and save. Keep the configured free model. The current default total request budget is `IF_MAX_REQUEST_TOKENS=32000`; update that value if reusing an older `.env`. Do not upload `.env` or put the key in HTML/JavaScript. If a key is already configured locally, do not overwrite it with the empty template.

## 4. Start the web interface

```powershell
uv run python app.py web --as-of 2026-10-27
```

Keep the terminal open, then open **http://127.0.0.1:8000** in your browser.

The date flag is the synthetic catalog's reference date, not today's date. All opportunities and employers are fictional. Normal browsing does not ask for a profile or academic form.

## 5. Try a conversation

Type one message at a time:

```text
I need an internship opportunity for AI in Riyadh
What are the requirements?
Are there any in Jeddah?
```

You can also click a suggestion. Press Enter to send or Shift+Enter for a line break. **New conversation** creates a fresh anonymous session.

## 6. Demonstrate an approved write (optional)

This demonstrates the course's human approval requirement. It is not required to browse.

Click **Academic details** and use fictional values:

| Field | Demo value |
|---|---|
| Major | Artificial Intelligence |
| Study year | 4 |
| GPA | 3.6 (out of 4) |
| Training type | Co-op |
| Required months | 6 |
| Available from | 2027-01-01 |

Click **Save session details**, then ask:

```text
Prepare a local draft for OP001 and show me the approval preview.
```

Review the separate approval card. **Decline** saves nothing. Ask again in a new turn, then **Approve & save locally** to save one draft. Asking for the same draft again returns the existing one. Nothing is submitted to an employer.

## 7. Stop and check

Press Ctrl+C in the terminal to stop the server. Restarting creates new browser sessions; local demo draft databases remain under ignored `runtime/` and are not part of submission.

```powershell
uv run python scripts/verify_local.py
uv run python scripts/readiness.py --require-live
```

The first command checks local contracts and real MCP without a key. The second checks committed current-source live evidence, including the browser and approval demonstration. A completed workflow alone is not a passing evaluation.

Terminal chat is also available:

```powershell
uv run python app.py chat --config B --as-of 2026-10-27
```

## Evaluation and key cleanup

Routine use requires only a local `.env`. Running the manual GitHub live evaluation requires the evaluator's own repository Actions secret `OPENROUTER_API_KEY`. This secret is separate from local `.env`; its value is never printed. The project owner's temporary evaluation secret is removed after final validation. Local contract CI and review of committed evidence work without it.

Only `.env.example` is submitted. If handing over an untracked folder manually, remove `.env` first; a GitHub-generated ZIP contains tracked files only. Remove/revoke your temporary key when you no longer need it. Keep the empty variable names and provider configuration so another evaluator can use their own key.
