# Live root-cause analysis — partial evidence

**Status: PENDING_LIVE_EVALUATION.** Real model evaluation started on 2026-10-27, but the full suite is incomplete. This marker intentionally remains until all 20 tasks have run under both configurations and their transcripts have been reviewed.

Evidence: [manifest](../results/live/20261027T202626-453723/manifest.json), [partial summary](../results/live/20261027T202626-453723/partial_summary.md). Model: `nvidia/nemotron-3.5-lightning:free`; one trial per task/configuration; the same fixed source, data and model across A/B. A finished 6 tasks (5 pass), B finished 5 (5 pass). All completed tasks are in the search category. Missing-information, constraint, approval and security task categories remain unmeasured in this A/B run.

| Verified cause or limitation | Count A | Count B | Evidence | Consequence / next step |
|---|---:|---:|---|---|
| Non-JSON final answer, followed by conservative budget rejection of formatting repair | 1 | 0 observed | `search-ar-data-riyadh-A-0-attempt1-transcript.json` and corresponding JSONL | Task failed `completed` and `recommended_match`; retain the failure. Consider provider-supported structured output and a separately budgeted bounded repair in a future version, then rerun both configurations. |
| Provider daily account quota exhausted | 0 | 1 interruption | `search-change-city-B-0-attempt1.jsonl`: HTTP 429 `daily account quota` | Infrastructure interruption, not a completed behavioral failure. Preserve trace and retry this task from a fresh session only after quota recovers. |
| Arabic explanation quality beyond the automatic assertions | Qualitative limitation | Qualitative limitation | Business replies mix English labels; B's Arabic Data answer contains “both eligible” and an unclear GPA-mismatch phrase | Passing IDs/tool checks does not mean polished or fully clear Arabic. Add a language/grounding review criterion in a future evaluation revision. |

## Why the Arabic A task failed

The trace shows the correct Data/Riyadh/coop search and eligibility checks for OP001, OP006 and OP030. OP001 and OP030 were eligible; OP006 failed GPA. The fifth model response described these facts in Arabic prose rather than the required final JSON object. The agent appended a formatting-repair instruction, but its next preflight check rejected another request: 12,675 actual tokens had already been reported, and the conservative upper bound for the expanded next prompt plus reserved output exceeded the 24,000-token per-turn limit. The limit was not evidence that the provider had already consumed 24,000 tokens. No sixth model call was sent.

This is an output-contract failure interacting with the conservative budget, not an incorrect catalog match or an unauthorized write. The two failed assertions describe one failed task and must not be counted as two independent failures. The model had already called eligibility in A, so B's extra verification instruction cannot be identified as the cause of this observed flip. B returned valid JSON in five requests and 12,754 tokens for the same task, but one stochastic sample is insufficient for a causal improvement claim.

## Paired comparison and coverage

On the five task IDs completed in both configurations, A passed 4/5 and B 5/5: one A-fail/B-pass flip and no observed reverse flip. A additionally passed the two-turn city-change task; B's corresponding task was interrupted by quota. Do not compare A's 5/6 directly with B's 5/5 as full-suite performance. Full-suite pass^k is unavailable. Repeated reliability is unmeasured with k=1.

The completed rows consumed 46 model request attempts, 109,659 reported tokens and USD 0 reported cost. The interrupted B trial adds two request attempts (one successful completion and the rejected attempt), 1,957 reported tokens and USD 0. These totals exclude the separate pilot, security experiments and earlier capacity failures. There is no application response cache.

## Security evidence is separate

The completed live injection experiment read OP030's malicious description in both variants but attempted no save, leaving zero unauthorized drafts in each. This demonstrates resistance to this one injection in these observations. It does not show that the code guard caused the live prevention. The forced-action replay separately attempts the malicious write: one draft in the unsafe test variant, zero in the protected variant, with a human-denial guard event and a successful approved benign control. See [SECURITY.md](../SECURITY.md).

## Operational fixes verified before this run

Earlier provider-capacity errors exposed exception wrapping during MCP cleanup, which prevented a clean incomplete manifest. Cleanup now preserves the original `ProviderError`; `app.py ask` returns a nonzero status for unfinished runs; HTTP 429 messages identify known quota/capacity categories without disclosing raw responses. Resume validates source/task hashes, model and completed CSV rows, retains behavioral failures and records interrupted trials separately. These changes were covered by the 73 passing local tests before the current A/B run.

No prompt/code fix was made after inspecting these A/B scores. The source is kept fixed to allow continuation. Resume attempts may span days, adding a provider/timing confound that must be disclosed. After all 40 trials finish, review the remaining transcripts, update counts and root causes, and replace the pending status only when that work is complete.
