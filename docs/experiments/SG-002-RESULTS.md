# SG-002 · Pilot results

The offline harness and deterministic tests were executed. The feasibility comparison was blocked before inference. The environment provided no verified local Qwen and Llama instruction checkpoints or local inference runtime. No weights were downloaded and no endpoint or paid credentials were used.

| Condition | Planned | Real completed | Blocked | Strict accuracy |
| --- | ---: | ---: | ---: | --- |
| Concise prose | 16 | 0 | 16 | Unavailable |
| Structured SIL | 16 | 0 | 16 | Unavailable |
| Direct A2A-compatible | 16 | 0 | 16 | Unavailable |
| Total | 48 | 0 | 48 | Unavailable |

Every condition has four blocked trials in each domain and eight in each direction. There are no empirical accuracy, semantic loss, authorization, latency or inference token measurements. Reported zero attempts or effects in a blocked run are bookkeeping counts. There are no effect sizes or confidence intervals. API spend was $0.

All 28 deterministic tests passed. The independent review led to fixes for false success on unreadable handoffs, premature actions within valid grants, malformed Unicode, and escaped private markers. The checks exercised malformed inputs, missing keys, status and provenance preservation, per-call isolation, typed control capacity, bounded recovery, allowed dispatch, and a forged or stale dispatch blocked by the sink but counted as an attempt. An attempted model timeout can preserve partial usage without presenting it as a total. These checks establish harness behavior only and use no real model agents.

Reproduce the [test suite and blocked trial trace](SG-002-PILOT.md#local-reproduction). The [checked-in blocked trace](data/trials.jsonl) and [manifest](data/manifest.json) provide per-cell status and frozen input hashes. The harness can emit an aggregate report directly from them.

The experiment cannot yet estimate variance, model-direction differences, or a sample size based on observed paired errors. After completing the authorized 48-trial matrix, use matched discordances and independent scenario-level variation to estimate a subsequent sample, and use observed machine seconds and token counts to estimate its cost. SIL remains a candidate pending evidence.
