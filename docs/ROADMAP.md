# Research roadmap

## SG-001 · Research and architecture

Record verified sources, compare five architecture hypotheses, propose decision-level semantics, and define a reproducible evaluation. The [ADR](decisions/ADR-001.md) remains proposed.

## Proposed SG-002 · Local benchmark prototype

After approval, build a disposable local harness with synthetic fixture packs for HERO-CAD, Archive, TAM Nexus and general-purpose handoffs. Start with prose, direct A2A, the structured core, and the compact JSON control. Add the fixed symbolic grammar and a referenced-artifact variant when the common fixtures and metrics are stable. Freeze the fixture challenge set before evaluation. Run independently configured agents across two local model families in both directions and publish traces, costs, errors, coverage and blind audit results. First run eight development fixtures, one authorized and one adversarial case per family, in both cross-family directions with seed 19 and three arms (prose, structured, direct A2A). Expand only after all 48 trials produce usable traces and the configured compute budget covers the next matrix. Report any unresolved feasibility limit before drawing adoption conclusions. Keep experiments offline and park negotiation and latent arms if reproducible support is unavailable.

Exit with an evidence-backed decision on whether a cross-domain profile adds value over reuse. Document the minimum meanings or fixture-specific rules that proved useful. A prototype is the deliverable. Production integration and specification approval are separate decisions.

## After SG-002 · Work justified by results

- Test bounded dictionary negotiation or latent, binary, and domain-native channels separately, with version mismatches, resource limits, fallback, and peer replacement in the fixtures.
- If evidence supports adoption, propose a read-only, local TAM Nexus pilot. Demonstrate trace reconstruction and policy enforcement before allowing state changes.
- Consider HERO-CAD and Archive adapters only after the pilot shows a working revision and provenance mapping. Keep the baseline supported while checking whether other agents benefit from the same semantics.
