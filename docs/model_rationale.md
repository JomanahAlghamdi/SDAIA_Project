> Historical model observations below are from the previous bilingual revision. The current conversational English source needs a fresh A/B run; no current pass rate is claimed. Original analysis is preserved in [history](history/2026-10-27/model_rationale.md).

# Model selection and external evidence

Reviewed 2026-10-27. Runtime verifies current zero pricing and tool support; no paid model or automatic fallback is enabled.

The initial candidate was `google/gemma-4-31b-it:free`. Authentication succeeded, but its live requests returned HTTP 429 indicating upstream capacity. An explicit pilot with `google/gemma-4-26b-a4b-it:free` returned the same category. These are availability failures, not measured quality scores.

The selected evaluation model is **`nvidia/nemotron-3.5-lightning:free`**. A real pilot completed the OP001 eligibility task in two model requests, using `check_eligibility`, with 4,040 reported tokens and USD 0 reported cost. That single pilot establishes connectivity and tool use, not suite accuracy.

NVIDIA's [official model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) reports PinchBench 83.43 and IFBench loose 72.88 for its NVFP4 checkpoint. These are vendor benchmarks, with different tasks and settings from this project. The OpenRouter deployment is not assumed to be identical to that checkpoint. Arabic is not in the card's stated supported-language list. The completed project evaluation found mixed-language wording and two English responses to Arabic prompts in B; these limitations remain even though B passed all automatic task assertions.

For comparison, Google's [official Gemma 4 page](https://deepmind.google/models/gemma/gemma-4/) reports retail tool-use benchmark τ2-bench scores of 86.4% for 31B Thinking and 85.5% for 26B A4B Thinking. Those results motivated the initial candidates but cannot substitute for this agent's own A/B results.

Both configurations in a completed comparison must use the same concrete model. Interrupted attempts and explicit model changes are recorded separately. No cross-benchmark ranking or improvement claim is made.

[OpenRouter's published free-tier limits](https://openrouter.ai/pricing) are 20 requests/minute and 50/day, rising to 1,000/day after at least USD 10 in credits have been purchased. Creating another key does not bypass account limits. The provider spaces requests by at least 3.2 seconds; a 429 still stops the run. No credits are purchased by this project.

Use `--resume results/live/<run>` after quota/capacity recovers to finish an incomplete v2 run. Source/task hashes, model, trial count and configurations must match. Completed behavioral failures are retained, not retried to improve scores. Infrastructure-interrupted trials are logged separately and retried from fresh session/database state, with new trace names. Resume attempts may span days, which adds a timing/provider-availability confound that must be reported.

## Measured project results

The complete 20-task A/B suite produced A 16/20 and B 20/20 on the automatic graders, one trial per task/configuration. Average requests were 3.40 / 3.50 and average tokens 7,926.3 / 8,344.0. Reported model cost was zero. See `results/live/20261027T202626-453723/summary.md` and `docs/error_analysis.md`, including incorrect prose in some passing tasks. These measurements justify selecting B for this prototype, not a general model ranking or a claim of perfect Arabic.
