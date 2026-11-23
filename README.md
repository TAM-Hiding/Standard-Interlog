# Standard Interlog

Standard Interlog (SIL) is a Stargazer research project on communication between heterogeneous AI agents. TAM Nexus is the motivating environment. A receiver should be able to act on a handoff without sharing the sender's model, tokenizer, reasoning architecture, vendor, or conversation history.

SG-001 is a documentation-only research milestone. The proposed first experiment tests whether a small, transport-independent semantic profile improves complete task outcomes over natural language, compact notation, and existing standards used directly. Each format can use whatever representation makes sense for its payload, subject to the experiment's controls. A shorter message is valuable when it reduces total cost while preserving the intended action, evidence, uncertainty, and authority boundaries.

## Terminology

- **Transport and orchestration** cover delivery, discovery, security context, and task lifecycle. Existing infrastructure can supply these functions.
- **Semantic profile** describes the meaning and scope of information exchanged, including what was observed, requested, verified, or left unresolved.
- **Encoding** is the representation of that information, such as prose, JSON, a symbolic vocabulary, binary data, or a model-specific latent payload.
- **Authorization** is a decision at the receiving boundary, based on an authenticated principal and applicable policy.

## Research documents

| Document | Purpose |
| --- | --- |
| [Literature review](docs/research/LITERATURE_REVIEW.md) | Existing standards, research results, limitations, and reusable implementations |
| [Architecture options](docs/architecture/ARCHITECTURE_OPTIONS.md) | Five hypotheses and the tradeoffs to measure |
| [Semantic core](docs/architecture/SEMANTIC_CORE.md) | Candidate meanings, trust boundaries, and example handoffs |
| [Benchmark plan](docs/benchmarks/BENCHMARK_PLAN.md) | Controlled comparisons across models, formats, and workloads |
| [ADR-001](docs/decisions/ADR-001.md) | Provisional direction and criteria for adoption |
| [Roadmap](docs/ROADMAP.md) | Proposed next scope and later decision points |

The profile is experimental. SG-001 contains no task measurements, implementation, or external standardization claim. Fixtures describe synthetic work in HERO-CAD, Archive, and TAM Nexus. Live integration requires separate approval.
