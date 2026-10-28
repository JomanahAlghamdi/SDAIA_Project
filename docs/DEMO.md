# Demonstrate Internship Finder

Use configuration B and the fixed synthetic catalog date. All opportunities, employers and fixture students are fictional. The ordinary assistant opens directly at `You:`.

## Ordinary conversation

```powershell
uv run python app.py chat --config B --as-of 2026-10-27
```

Type each message after the previous answer:

```text
I need an internship opportunity for AI in Riyadh
What are the requirements?
Are there any in Jeddah?
/quit
```

The first request should retrieve AI candidates in Riyadh, the second explain published requirements, and the third retain AI while changing the city. No academic details are required. A search candidate is not a verified personal eligibility decision.

## Separate approved-write demonstration

For this advanced demonstration only, explicitly load fictional fixture S001:

```powershell
uv run python app.py chat --config B --student S001 --as-of 2026-10-27
```

Ask `Prepare a local draft for OP001 and show me the approval preview.` Review the host's preview. Enter `NO`: nothing is saved. Ask again in a new turn and enter exactly `YES`: one local draft is saved. Ask to save the same opportunity once more: the existing draft is returned without duplication. No employer application is sent.

S001 is an explicit test option, never the default user. Its local drafts persist between fixture sessions, so a repeated demonstration may immediately report an existing draft. To demonstrate consent from a fresh state, start ordinary chat and use `/details` with fictional values (Artificial Intelligence, year 4, GPA 3.6, coop, 6 months, available 2027-01-01); each normal chat starts in a new isolated session. Normal chat can optionally collect fictional academic facts with `/details` for the same check/write flow.

## If the model is unavailable

The actual evaluation transcripts under `results/live/` are recorded observations, with source hashes and usage metrics. `uv run python app.py demo --interactive` demonstrates the four real tools, MCP and consent using a clearly labeled scripted provider; it is NOT a live AI demonstration or a replacement for the live evaluation.
