# Partial live evaluation — not a complete suite

Run: `20261027T202626-453723`. Model: `nvidia/nemotron-3.5-lightning:free`. One trial per task/configuration.

**11/40 completed; 29 remain.** The next B trial stopped on HTTP 429 (daily account quota). The manifest retains the interrupted trial separately. Source and task hashes match; resume validation succeeded without model calls.

| Config | Completed / planned | Passed among completed | Avg requests | Avg tokens | Reported cost |
|---|---:|---:|---:|---:|---:|
| A | 6 / 20 | 5 / 6 (83.3%) | 4.50 | 10,654.2 | $0.00 |
| B | 5 / 20 | 5 / 5 (100.0%) | 3.80 | 9,146.8 | $0.00 |

All completed tasks are search tasks. The five paired task IDs have A 4/5 and B 5/5, one A-fail/B-pass flip and no observed reverse flip. The unpaired city-change task passed in A; B was interrupted. Do not interpret the unequal subset scores as full-suite performance or a causal improvement. Full-suite pass^k is not available.

The failed A Arabic task returned prose instead of final JSON, then the conservative preflight token check blocked formatting repair. The behavioral failure is retained. See [root-cause analysis](../../../docs/error_analysis.md).

Completed rows: 46 model request attempts, 109,659 reported tokens, $0. Interrupted B trial: 2 attempts, 1,957 tokens, $0. Pilot/security/older capacity failures are separate. No application response cache.

After account quota recovers, with the same source and model:

```bash
uv run python -m evals.run --config A B --trials 1 --resume results/live/20261027T202626-453723
```

Continuation retains completed behavioral failures, retries only infrastructure-interrupted/unstarted trials and records each attempt. Runs across days introduce a timing/provider confound.
