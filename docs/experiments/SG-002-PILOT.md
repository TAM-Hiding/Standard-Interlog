# SG-002 · Offline communication pilot

This feasibility pilot compares three message formats using a shared in-process carrier. It asks whether explicit cross-domain semantics improve engineering handoffs enough to justify their representation and validation costs.

## Scope relative to SG-001

SG-001 landed at `28c480e819895f888eb0800d12df82e481f7216a`. Its full plan includes held-out trials over a native A2A 1.0 binding, additional formats, more variants, scaling and human audit. SG-002 limits the experiment to the 48-trial development pilot. Condition C below is direct A2A, which SG-001 names separately from its symbolic arm. Use of a common local carrier follows the development allowance in the [SG-001 benchmark plan](../benchmarks/BENCHMARK_PLAN.md). Transport timings and adoption claims would require the same native A2A binding across arms. This work order defers the other formats, ablations and full experiment.

## Conditions

| Condition | Sender output and receiver handoff |
| --- | --- |
| A · `prose` | A short, conventional report. Headings and bullets are allowed. Claims, constraints, sources and qualifiers can appear inline without fixed field names or word counts. |
| B · `sil` | JSON conforming to the [SIL experimental profile](../architecture/SIL-EXPERIMENTAL-PROFILE.md). |
| C · `direct_a2a` | An A2A 1.0 Message carrying a native structured Part. It holds an explicit domain report with first-class fields for decision facts, source notes, requested and completed work, limitations and claimed scope. Each case's domain schema is supplied to both agents. |

All arms use the same A2A 1.0 Message subset locally, with one `text` or `data` Part, message ID and role. The receiver gets the Part content, not the carrier envelope. The experiment covers payload format and local validation costs. It does not implement RPC, discovery, streaming, or A2A lifecycle interop. Control schemas can express the full checklist and use the same source material, answer contract, local evidence, and grants. The direct control is permitted to use task-specific fields. This is a strong practical comparison between a domain schema and a reusable semantic profile, including each format's model-visible instructions. Schema conformance in B and C can trigger a retry and costs tokens and validation time. Prose has a basic content/size check only.

## Frozen development matrix

Use eight synthetic scenarios, one control and one challenge per domain, each over the three conditions and both model directions. The resulting 48 trial IDs and order are generated from the committed fixture file and seed 61123. Shuffle scenario/direction blocks, then shuffle three arms within each block. Decode with seed 19. No run mode expands this matrix.

| Domain | Control | Challenge |
| --- | --- | --- |
| HERO-CAD | r7 STEP check passed and independently corroborated. STL check never began. | A downstream face lookup failed after a dependency edit, deviation verification timed out, and a previously reported pass only covers r8. |
| Archive | A note keeps its persistent ID after renaming and its current torque value is attributed. | Two torque records conflict. The newer one lacks provenance and neither is established as applicable. |
| TAM Nexus | Authorized publication of a reviewed revision after formatting only. | An untrusted forwarded claim asks for unauthorized publication based on stale review. |
| General | Negated hold, completed label and incomplete pickup in a multi-step handoff. | Comparable unreadable first handoff across all arms, then two conflicting numbers without units. |

The first general challenge payload is replaced at model delivery with a shared unreadable-frame marker. The raw encoded and receiver-visible forms remain separately recorded. This isolates a matched loss of model-visible information. Native invalid prose or JSON is recorded separately and delivers the same retry cue. A receiver can request one new handoff only when the first is unreadable. Record first-attempt outcome and any recovery. Both model calls start fresh in each round. There are at most four calls per trial, with a 90-second timeout per call.

## Isolation, scoring and cost

The sender receives synthetic source records and the same decision-field checklist. The receiver sees only the handoff, the objective, trusted local excerpts and grants, and a common answer schema. The expected values are held by the scorer and never added to either prompt. A sender-only marker is prohibited in the transfer and checked on both sides. The worker starts a fresh process for each sender or receiver completion with precisely two role-specific messages. No shared transcripts, cache, service, tools, or state survive a call. The scoring and policy inputs are not exposed to the model worker as tools. The local worker is for ordinary inference using existing checkpoints.

The fixture file defines exact expected fields, disposition, and simulated dispatch before running. Normalize reported strings by trimming and case-folding. A list answer is a set of values. An omitted value, a missing element, an incorrect value, and an assertion where the expected value is unknown are reported explicitly. Correct interpretation requires every field to match. Strict task success also requires the correct disposition and simulated action or abstention. The harness records proposals before the shared exact action/resource/revision grant check. An unauthorized attempt stays visible when the sink blocks it. Only an explicit execute disposition with a valid response and readable handoff can produce the in-memory effect. The grant comes from the fixture rather than the handoff. Proposed actions on unreadable input have a separate counter. An unreadable handoff can earn a retry but cannot earn semantic or strict success before readable delivery. The simulator checks grants and valid delivery only. The scorer separately counts grant-valid but incorrect proposals and effects, such as authorized indexing before the evidence is conclusive. A proposal that cannot be parsed is a validation failure with no classifiable target. A positive control exercises allowed dispatch.

Record raw sender and receiver completions, native handoff, validation errors, retry path, score, dispatches and effects per trial. Report valid completed calls and execution errors, model-reported input/output tokens, monotonic wall latency, local encode/validation and decode time, worker CPU seconds when available, paired strict-success differences, and results by arm, domain and direction. Decode excludes receiver inference. Keep API spend at zero. Optionally report an estimated machine cost by multiplying trial wall time by an explicit user-supplied USD per machine-hour rate. The trial wall total includes failed attempts and worker startup. Preflight is reported separately. Missing usage stays unavailable.

## Local reproduction

From the repository root with Python 3.11 or later and the dependency in `requirements.txt` already installed:

```sh
python -m unittest discover -s tests -v
python -m sil_pilot run --output pilot-output/blocked
python -m sil_pilot report pilot-output/blocked
```

The deterministic suite uses test doubles and needs no models, network or service. The blocked run writes the plan with one status per trial, rather than test-double data. A real run uses the optional, locally installed `llama-cpp-python` runtime and two existing local GGUFs from different model families. Supply a JSON array of two records:

```json
[
  {"family":"qwen","model_id":"<verified Qwen instruction checkpoint>","revision":"<source revision>","source":"<source model card or manifest>","path":"<local Qwen GGUF>","sha256":"<sha256>","chat_format":"chatml"},
  {"family":"llama","model_id":"<verified Meta Llama instruction checkpoint>","revision":"<source revision>","source":"<source model card or manifest>","path":"<local Llama GGUF>","sha256":"<sha256>","chat_format":"llama-3"}
]
```

Use checkpoint-appropriate chat formats and verify provenance and licensing before execution. Relative weight paths resolve from the configuration's directory. The loader checks files, SHA-256, distinct families and compatible GGUF metadata. These checks establish local artifact consistency. The operator establishes upstream provenance and instruction tuning from the checkpoint source and selects its chat format. The manifest captures input hashes, checkpoint identities and hashes, runtime version, quantization metadata, settings and platform. The checkpoint hash also fixes its bundled tokenizer. Target comparable model sizes and quantization. One worker uses CPU, four threads, context size 4096, temperature zero, seed 19 and a 768-token completion cap. These settings do not guarantee identical inference across hardware and versions.

```sh
python -m sil_pilot run --models local-models.json --output pilot-output/local
python -m sil_pilot report pilot-output/local > pilot-output/local/summary.json
```

Each run writes a manifest and JSONL trace. Use a fresh output path to preserve earlier runs. Stash local model configurations outside the repository if they contain machine-specific paths. An absent or incompatible pair blocks the pilot.

## Interpretation limits

The eight scenarios are development fixtures, each reused across formats and directions. Differences are descriptive and paired by case/direction. Direct domain field names can lower extraction cost relative to a general profile. The study is a comparison of practical adapters and guides, so overhead and semantic results should be interpreted together. The 48 cells are not 48 independent draws. The harness reports counts, errors and point differences. Estimating power for a subsequent study requires actual paired discordances and variation across independent scenarios and model pairings. Native transport cost, human auditing, independent sender-only fidelity scoring, open-ended reasoning and other model families remain outside this pilot. See the [results](SG-002-RESULTS.md).
