# Live root-cause analysis — PENDING

**Status: PENDING_LIVE_EVALUATION.** No model-generated A/B outcome has been observed in this build environment. Do not replace this status with invented values.

After a complete run, use its summary, graded transcripts and tool traces. Distinguish bad extraction, overly narrow/broad search, missing verification, ignored constraints, wrong tool choice, tool failure, malformed final JSON and provider/quota failures. A failed assertion is a symptom; inspect the trace before assigning a cause.

| Verified root cause | Count A | Count B | Example task / trace | Change tried | Outcome / next step |
|---|---:|---:|---|---|---|
| Pending live execution | — | — | — | B adds one eligibility-verification instruction | Not measured |

Record improvements **and regressions**. Use the same model, tasks and configuration hashes. If further code/prompt changes are made, rerun both configurations and retain the old run separately. Do not treat one successful run as reliable repeated behavior. Document k, provider errors and any missing tasks.

Before final submission: replace the pending table with evidence, include the actual live run directory and its hash manifest, and summarize what you would change next. Update the README evaluation table from the same run.
