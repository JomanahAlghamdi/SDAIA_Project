# Model choice and measured tradeoffs

The selected concrete model is `nvidia/nemotron-3.5-lightning:free` through OpenRouter. Both A and B use this same model. Before calling it, the adapter retrieves current metadata and requires tool support and zero pricing. It never silently switches to a paid model or to a router alias.

The choice combines tool availability, English support, public benchmark context and this project's own measured behavior. NVIDIA's [official model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) describes a 30B-parameter mixture-of-experts model with 3B active parameters and reports PinchBench 83.43 and IFBench loose 72.88 for the NVFP4 checkpoint. Those vendor results use different tasks and settings; they are not this project's accuracy and do not prove the OpenRouter endpoint is the identical deployment.

The initial Gemma candidates encountered upstream HTTP 429 failures, documented in the [historical rationale](history/2026-10-27/model_rationale.md). They have no comparable project quality score. No cross-benchmark model ranking is claimed.

## Project observations

| Source revision | Experiment | A | B | Interpretation |
|---|---|---:|---:|---|
| Historical bilingual revision | 20 tasks, one trial/config | 16/20 | 20/20 | Historical only; passing assertions missed some misleading prose |
| `c1ef6099` | First 25-task English review | 17/25 | 19/25 | Token reservation fixed, but browsing/eligibility contracts were confused |
| `2ca07085` | Reasoning-off experiment | 18/25 | 17/25 | Basic browsing improved; city follow-ups and write workflows regressed |
| `0c7ca0d7` HTML revision | Four-task pilot, six-turn browser, full 25×2 | 25/25 | 24/25 | One B personal city-follow-up failure; no claim that B outperforms A |

Current metrics are in [`results/current_run_status.json`](../results/current_run_status.json); actual final-response review is in [error analysis](error_analysis.md). Behavioral failures remain in the CSVs and are never silently retried for a better score.

## Reasoning and budget choice

The reasoning-off experiment reduced usage but produced announcements instead of tool calls, unsupported “no opportunities” answers, and refusals to use available draft tools. NVIDIA documents this class of [reasoning-off tool-calling limitation](https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent/blob/main/docs/how-to/configure-llm.md).

The current adapter requests reasoning when supported, with a 1,024-token allocation and a 3,072-token combined generated-output cap. The per-turn total ceiling is 32,000 tokens, alongside 8 model calls, 20 tool calls and the context/result caps. These are finite limits, not unlimited retries. Actual provider usage is enforced before tool execution, and response repair is limited to one attempt. [OpenRouter explains](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) that reasoning can consume the output budget; finish reason and reasoning-token counts are recorded when supplied. Requesting a reasoning allocation is not presented as an exact measurement of the upstream implementation.

The HTML and CLI use the same agent/provider; the interface adds no model proxy, API-key input in JavaScript, or extra hosted service. The owner temporarily uses their key for evaluation; the evaluator supplies their own `.env` afterward.

## Reproducibility limits

Temperature is fixed at zero, but hosted outputs are not guaranteed deterministic. One trial per task does not establish repeated reliability or statistical significance. Effective model names, request counts, tokens, cost, source fingerprints and budget settings are recorded.

Requests are paced at least 3.2 seconds apart. A provider error stops the run. Only infrastructure-interrupted trials in an explicitly resumed, matching-source experiment may be attempted again; completed behavioral failures are retained. A complete run cannot be resumed for a better score. No credits are purchased and no deployment-wide daily spending cap is claimed.
