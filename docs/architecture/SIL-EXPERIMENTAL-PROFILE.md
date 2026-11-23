# SIL experimental JSON profile

The pilot profile carries claims, constraints, work status, scoped check results and sender-reported authorization. The reusable semantics are payload data independent of transport. The [JSON Schema](../../schemas/sil-experimental.schema.json) defines the pilot envelope. The local carrier supplies correlation. Real identity, current revision and authorization must come from the host and policy boundary.

| Field | Meaning |
| --- | --- |
| `intent` | Request, report, or clarification. |
| `claims` | Observations, interpretations, predictions or reported verifications. Each statement carries its uncertainty and source relationships. Preserve negation and conflicts in the statement and attributed evidence. |
| `constraints` | Conditions a receiver must honor. |
| `action` | Requested and completed work. A request does not authorize execution. |
| `taskStatus` | Completion of the reported work as a whole. |
| `checks` | Scoped criterion, revision, verdict, verifier, and source references. |
| `reportedScope` | A nullable claim about scope. The receiver uses trusted grants for decisions. |

A completed handoff may contain a failed check. A check is `not_run` when it never started, `inconclusive` when it started without establishing a verdict, and `unknown` when its disposition is unavailable. Passing and failing require a reported verifier and a supporting reference. This is a shape constraint. The receiver needs independent local evidence, or an acceptable attestation, to call it receiver-confirmed. Missing or conflicting evidence remains visible. References in payloads are inert labels in the pilot.

```json
{
  "profile": "sil-experiment/0",
  "intent": "report",
  "claims": [{
    "statement": "The r9 chamfer face reference could not be resolved.",
    "kind": "observation",
    "certainty": "asserted",
    "evidence": [{"source": "CH-62", "relation": "supports"}]
  }],
  "constraints": ["Defer STEP registration until r9 verification is complete."],
  "action": {"requested": null, "completed": ["Rebuilt the pad on r9."]},
  "taskStatus": "partial",
  "checks": [{
    "check": "downstream-face",
    "criterion": "Chamfer face resolves after rebuild",
    "revision": "r9",
    "outcome": "failed",
    "verifier": "Emi",
    "evidence": [{"source": "CH-62", "relation": "supports"}]
  }],
  "reportedScope": null
}
```

The format uses strict JSON without duplicate keys. The adapter rejects bad shape, unknown fields and oversized outputs. Missing facts can still pass shape checks, so the experiment separately scores receiver interpretation. Payload strings never become commands or grants.
