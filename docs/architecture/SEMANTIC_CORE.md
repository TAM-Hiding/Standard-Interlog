# Candidate semantic core

This is a model of meaning for the benchmark. Names and examples are illustrative. A conforming transport could already carry much of the envelope. The experiment should ask which remaining meanings require an explicit profile.

| Concept | Minimum useful meaning |
| --- | --- |
| Identity and capabilities | Carrier-authenticated principal, locally resolved agent identity, advertised capabilities and supported profile/payload versions. Capabilities describe what the peer can parse or do. |
| Correlation | Message ID in sender scope, task ID in orchestration scope, reply or parent reference, and target resource revision where applicable. A retry retains its logical operation identity. |
| Intent | Distinguish request, report, and clarification. Requests specify action, target, hard requirements, preferences, and relevant scope. A report can carry several claims. |
| Claims | Identify the proposition, subject/scope and revision, and distinguish observation, interpretation, prediction, and verified result. Preserve positive or negative polarity and unknowns. |
| Evidence and provenance | Link each consequential claim to supporting, contradicting, or missing evidence. Records can identify the source, artifact version or digest, method, and observation time. Mark unavailable or redacted evidence explicitly. |
| Uncertainty | Preserve unknown, disputed, or tentative states and their reason. Any numerical confidence remains a sender estimate with an identified scale and calibration basis. |
| Authority | Describe requested permissions or refer to an external policy record. Validate actual authority at dispatch and at action time. |
| Result and failure | Communicate task status and per-check outcomes separately. Include stable failure categories where needed, affected target, and whether retry or clarification is appropriate. |
| Versioning | Advertise supported versions through existing capability channels or provisioning. Use a common understood profile. Unknown required meaning blocks the affected decision. |

An **observation** records what a source or tool reported. An **interpretation** explains an observation and cites what it depends on. A **prediction** concerns an unobserved or future state and identifies assumptions. A **reported verified result** identifies the verifier, scoped procedure, criterion, subject revision, and evidence that the procedure was carried out. The receiver records independent verification only after checking the evidence or an attestation acceptable under local policy. Receipt of the report proves delivery at most. Claims can be challenged independently, and source authenticity alone does not establish truth. Preserve contradictory claims with separate attribution. Absence of a proposition is unknown unless the reporting contract explicitly defines the relevant inventory as complete.

## Check outcomes

| Outcome | Condition | Example consequence |
| --- | --- | --- |
| `passed` | The check executed against the named revision and evidence shows that its criterion was met. | Accept that criterion for that revision. |
| `failed` | The check executed and evidence shows the criterion was violated. | Report the violation and preserve diagnostic evidence. |
| `not_run` | The check never began. Record why when known. | Request or schedule a run if needed. |
| `inconclusive` | The check began, but interruption, ambiguity, missing output, or invalid measurement prevented a reliable verdict. | Collect evidence or repeat the check before treating the criterion as resolved. |

If execution itself is unknown, retain that epistemic state or request clarification. A process error can be an observation or a failed *process-exit* check while the geometry check remains inconclusive. A completed orchestration task can deliver an inconclusive report. Test results never imply permission to publish.

## Example handoffs

The example IDs and revisions are synthetic. A carrier would supply authenticated sender and task correlation where available.

```json
{
  "profile": "sil-experiment/0",
  "task": "cad-17",
  "intent": "report",
  "revision": "bracket:r7",
  "checks": [
    {
      "id": "step-round-trip",
      "criterion": "one solid after reopening",
      "outcome": "passed",
      "evidence": ["step-reopen-log:r7#12"]
    },
    {
      "id": "downstream-reference",
      "criterion": "chamfer target resolves after pad change",
      "outcome": "failed",
      "evidence": ["regen-log:r7#18"]
    },
    {
      "id": "stl-watertight",
      "outcome": "not_run",
      "reason": "STL export was out of scope"
    },
    {
      "id": "mesh-deviation",
      "outcome": "inconclusive",
      "reason": "checker started and timed out",
      "evidence": ["mesh-check-log:r7#9"]
    }
  ]
}
```

- **HERO-CAD.** The regeneration log observes an unresolved face reference. A dependency report says the pad width changed. The interpretation that this change caused the unresolved reference remains tentative pending comparison with the previous revision. The STEP check applies to the reopened export of r7 and says nothing about the missing STL check.
- **Archive.** Retrieval returns revisions 3 and 4 of persistent note `note-42` with different torque values. Preserve both source locators and units. Record that no applicable drawing revision is available. Editing the note title keeps its persistent ID. A revision ID still selects which wording was seen.
- **TAM Nexus.** A coordinator asks for an independent read-only review of candidate `r7`, referencing scoped shared context. A worker reports success on `r6` while another worker updates the candidate. Keep the old result with its revision, compare the current revision before execution, and ask for fresh evidence. A review request grants neither write nor publish access.
- **General purpose.** A receiver gets two observations with contradictory applicability dates and a malformed recommendation. Preserve the observations, record the invalid recommendation, and request a corrected message with the same task correlation, a new message ID, and a reference to the message it corrects. Apply no action based on an unresolved date.

## Trust and transport boundary

Keep identity and access enforcement in the host or carrier. Treat claimed sender, tool descriptions, reference contents, and optional payloads as untrusted data. The receiver resolves authenticated principal, action, resource, scope, and revision against local policy before invoking side effects. A forwarded permission claim or advertised skill cannot expand authority. Check expiry and revocation when the backing authority supports them. Use least privilege for evidence retrieval, cap payload size and decode depth, and avoid fetching unsolicited locations or executable content. When semantics or artifact versions disagree, stop the affected action and request clarification.

At the action sink, enforce the revision precondition and record the scoped operation ID atomically with the state change, for example in one transaction. If a sink cannot ensure conditional, idempotent execution, keep it read-only in the experiment. A transport retry keeps the same operation identity and content. Reuse with changed content is a conflict. Corrected communication gets a new message ID and identifies the superseded message. Preserve message and evidence references, authenticated acting principal and verified delegation context where applicable, the applied policy decision, result, and parser/profile version subject to retention and redaction policy. Avoid logging credentials or reproducing data beyond the auditor's access.

Map task lifecycle, message IDs, identity context, capabilities, and attachments to [A2A's existing model](https://a2a-protocol.org/v1.0.0/specification/) where the mapping preserves meaning. A structured Part can carry claim and check semantics; per-check results stay distinct from A2A's task state. MCP can expose authorized tools or resources backing the evidence. An in-process queue can carry the same data with locally provisioned identity, profile versions, permissions, and artifact resolution. Each adapter retains its trust boundary and reports mappings it cannot preserve.

Open questions include minimum evidence quality for consequential claims, how to scope IDs across adapters, vocabulary ownership for domain-specific claims, and whether explicit confidence fields improve decisions or merely encourage false precision.
