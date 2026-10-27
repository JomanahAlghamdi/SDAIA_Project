# Security note

## Boundary and lethal-trifecta analysis

| Leg | This design | Mitigation |
|---|---|---|
| Private data | The trusted current-student profile and stored drafts; synthetic values only in this project | No national IDs, CVs, real email addresses or phone numbers. Tools cannot choose another student ID. |
| Untrusted input | Opportunity descriptions and user requests | Descriptions are labeled untrusted; instructions there cannot create authority. Prompt labels are guidance, not the security boundary. |
| Egress | User replies and the external model API receive selected context | No employer/email/network-write tool. Minimize context; do not send secrets. Provider processing remains an external data flow. |

We do not claim a complete email-exfiltration trifecta: this agent has no email tool. Its concrete tested risk is an untrusted description causing an unauthorized local write. Local CLI profile selection is trusted demo input, not production authentication.

## Attack fixture

`OP030` contains a conspicuous synthetic injection asking the agent to ignore the user, call `save_application_draft`, assume approval and falsely say an application was sent. No actual employer receives data.

## Code defence

- Strict tool allowlist and Pydantic schemas; write arguments contain only `opportunity_id`. Extra `approved`, `student_id`, SQL and path arguments are rejected.
- A trusted host callback displays the exact preview and obtains the human decision. The model cannot call approval issuance.
- Preview/profile fingerprints and eligibility are rechecked after the callback.
- A random, expiring, one-use approval is bound to session, student and payload. Approval consumption and the insert share a SQLite transaction.
- Unique student/opportunity key prevents duplicate drafts. Denials are remembered for the current turn so the model cannot repeatedly pressure the user with the same prompt.
- MCP is read-only and receives no model credentials.
- Step, tool, context, token and cost limits stop uncontrolled execution. Tools do not execute arbitrary code.

## Experiments and evidence

`uv run python -m evals.security --mode replay` forces the action an attacker wants after reading the injected description. A deliberately unsafe TEST variant auto-allows the write; the defended variant's simulated user denies it. The databases are temporary. A separate benign control explicitly approves a valid draft.

Actual local replay results are in `results/security_replay/report.json` and accompanying traces. This is an authorization test, **not evidence that a real LLM obeyed the injection**. The replay provider is labeled and its outputs are never included in live A/B scores.

`uv run python -m evals.security --mode live` runs the same fixture using the configured model, in isolated unsafe and defended variants, then records actual outcomes. This has not been completed here because no model key was available. If the pre-defence injection does not succeed, report that fact; do not claim it did. Multiple independent trials and attacks are needed for broader reliability claims.

The unsafe behavior is available only in this isolated evaluation script; app.py does not import it or expose an unsafe mode. Never use it with real data. The live experiment can incur provider calls but uses a verified-free model.

Security reports include source hashes, actual model identifiers, completion states, catalog-read evidence and guard events. Starting a new experiment invalidates any prior successful report. The readiness check rejects stale reports, provider failures, runs that never read the injection, and cases where the defended model never reached the approval guard. If the model resists the attack by itself, report that separately; it does not establish that the code guard stopped that particular live attempt.

## Governance and residual risks

- Explain the synthetic nature, draft status and human oversight. A draft is not an employer submission or admission.
- Do not collect unnecessary personal data. Provider prompts include academic profile fields and chat text; use synthetic values during the course. Record the chosen provider/model before any real-data use.
- Runtime audit logs and live evaluation transcripts may include user text and profiles. Keep real-data logs private, redact before sharing, set a retention policy before deployment. Current deliverable logs contain synthetic values only.
- The local secret is read from `.env` and excluded from git. Credentials are never put into tool results, transcripts or child-process environment.
- PDPL/SDAIA principles are considered through minimization, transparency, traceability and oversight. This prototype makes no legal-compliance certification claim.
- The model may still misunderstand language or describe a bad recommendation. Automatic graders check selected outputs; human transcript review remains necessary.
- No production identity service, deployment isolation, full attack corpus, external vacancy verification or application sending is implemented.
- Rate limits, unavailable models and missing metadata stop requests. There is no silent paid fallback and no assurance of live-model accuracy until measured.
