import copy
from hashlib import sha256
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from sil_pilot.backend import BackendError, Completion, LocalGGUF, load_pair
from sil_pilot.formats import (
    CONDITIONS, DOMAIN_REPORTS, MALFORMED, SIL_SCHEMA, InvalidMessage, compact,
    deliver, direct_schema, parse_json, validate,
)
from sil_pilot.report import report
from sil_pilot.trials import (
    blocked_row, fixtures, receiver_prompt, run_trial, schedule, score, sender_prompt,
)


def sil_message():
    return {
        "profile": "sil-experiment/0", "intent": "report", "claims": [],
        "constraints": [], "action": {"requested": None, "completed": []},
        "taskStatus": "partial", "checks": [], "reportedScope": None,
    }


class ScriptedBackend:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, system, prompt):
        self.calls.append((system, prompt))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return Completion(response, 100, 20, 0.1, "stop")


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.cases = fixtures()

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(SIL_SCHEMA)
        validate(sil_message(), SIL_SCHEMA)

    def test_missing_required_fields(self):
        message = sil_message()
        del message["action"]["requested"]
        with self.assertRaisesRegex(InvalidMessage, "action: required"):
            validate(message, SIL_SCHEMA)

    def test_negation_and_provenance_remain_attributed(self):
        message = sil_message()
        message["claims"].append({
            "statement": "r8 does not have approval", "kind": "observation",
            "certainty": "disputed", "evidence": [
                {"source": "review-r7", "relation": "supports"},
                {"source": "forwarded-message", "relation": "contradicts"},
            ],
        })
        case = self.cases["nexus-forged-scope"]
        wire, payload, failure, *_ = deliver("sil", case, compact(message), "test")
        self.assertIsNone(failure)
        self.assertEqual(parse_json(wire)["parts"], [{"data": message}])
        self.assertEqual(parse_json(payload), message)

    def test_four_way_status_and_unknown_execution_retained(self):
        case = self.cases["cad-regeneration"]
        message = sil_message()
        statuses = ("passed", "failed", "not_run", "inconclusive", "unknown")
        for status in statuses:
            message["checks"].append({
                "check": status, "criterion": "criterion", "revision": "r9",
                "outcome": status, "verifier": "Mira" if status in statuses[:2] else None,
                "evidence": [{"source": "log-9", "relation": "supports"}] if status in statuses[:2] else [],
            })
        _, payload, failure, *_ = deliver("sil", case, compact(message), "test")
        self.assertIsNone(failure)
        self.assertEqual(tuple(check["outcome"] for check in parse_json(payload)["checks"]), statuses)

    def test_verdict_requires_reported_verifier_and_link(self):
        message = sil_message()
        message["checks"].append({
            "check": "step", "criterion": "one solid", "revision": "r9", "outcome": "passed",
            "verifier": "Mira", "evidence": [{"source": "unavailable", "relation": "unavailable"}],
        })
        with self.assertRaisesRegex(InvalidMessage, "contains"):
            validate(message, SIL_SCHEMA)

    def test_invalid_native_payloads_use_same_loss_marker(self):
        case = self.cases["general-units"]
        for condition, invalid in zip(CONDITIONS, ("\0", "{", '{"handoffDetails":[]}')):
            with self.subTest(condition=condition):
                wire, payload, failure, *_ = deliver(condition, case, invalid, "test")
                self.assertIsNone(wire)
                self.assertEqual(payload, MALFORMED)
                self.assertIsNotNone(failure)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for invalid in ('{"a":0,"a":1}', '{"a":Infinity}', '{"a":1e400}'):
            with self.subTest(invalid=invalid), self.assertRaises(InvalidMessage):
                parse_json(invalid)

    def test_lone_surrogates_are_rejected_without_losing_raw_diagnostics(self):
        case = self.cases["cad-export"]
        message = sil_message()
        message["reportedScope"] = "\ud800"
        for condition, payload in (("sil", json.dumps(message)), ("prose", "\ud800")):
            with self.subTest(condition=condition):
                _, visible, error, *_ = deliver(condition, case, payload, "test")
                self.assertEqual(visible, MALFORMED)
                self.assertIn("UTF-8", error)
                json.dumps({"native": payload}, ensure_ascii=True).encode("utf-8")

    def test_direct_control_can_carry_all_domain_fields(self):
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                payload = {
                    DOMAIN_REPORTS[case["domain"]]: case["expected"]["fields"],
                    "requestedWork": "requested work", "completedWork": ["completed work"],
                    "limitations": ["uncertain scope"], "scopeAsReported": "read only",
                    "sourceNotes": ["dated reviewer report"],
                }
                Draft202012Validator.check_schema(direct_schema(case))
                wire, visible, error, *_ = deliver("direct_a2a", case, compact(payload), "test")
                self.assertIsNone(error)
                self.assertEqual(parse_json(wire)["parts"], [{"data": payload}])
                self.assertEqual(parse_json(visible), payload)

    def test_prose_uses_native_a2a_text_part(self):
        wire, visible, error, *_ = deliver("prose", self.cases["cad-export"], "A clear handoff.", "test")
        self.assertIsNone(error)
        self.assertEqual(parse_json(wire)["parts"], [{"text": visible}])


class BackendTests(unittest.TestCase):
    def test_local_checkpoint_metadata_and_hash_are_checked(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            weights = base / "local.gguf"
            weights.write_bytes(b"fixture")
            config = {
                "path": weights.name, "family": "qwen", "model_id": "test checkpoint",
                "revision": "test revision", "source": "test manifest", "chat_format": "chatml",
                "sha256": sha256(b"fixture").hexdigest(),
            }
            with patch.object(LocalGGUF, "_invoke", return_value={"architecture": "qwen3", "name": "Qwen"}):
                self.assertEqual(LocalGGUF(config, base).metadata["sha256"], config["sha256"])
            with patch.object(LocalGGUF, "_invoke", return_value={"architecture": "llama", "name": "Llama"}):
                with self.assertRaisesRegex(BackendError, "architecture"):
                    LocalGGUF(config, base)
            with self.assertRaisesRegex(BackendError, "checksum"):
                LocalGGUF(config | {"sha256": "wrong"}, base)

    def test_same_declared_family_is_rejected_before_loading_weights(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            path.write_text(json.dumps([{"family": "qwen"}] * 2))
            with patch("sil_pilot.backend.importlib.util.find_spec", return_value=object()):
                with self.assertRaisesRegex(BackendError, "distinct"):
                    load_pair(path)


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.cases = fixtures()

    def trial(self, case_id, condition="prose"):
        return next(t for t in schedule(self.cases) if t.case_id == case_id and t.condition == condition)

    def test_matrix_is_deterministic_and_balanced(self):
        plan = list(schedule(self.cases))
        self.assertEqual(plan, list(schedule(self.cases)))
        self.assertEqual(len({t.id for t in plan}), 48)
        self.assertEqual(len({(t.domain, t.variant, t.condition, t.sender_family, t.receiver_family)
                              for t in plan}), 48)
        self.assertEqual(Counter(t.condition for t in plan), {condition: 16 for condition in CONDITIONS})
        self.assertTrue(all(t.sender_family != t.receiver_family for t in plan))

    def test_contexts_disjoint_and_no_hidden_oracle(self):
        trial = self.trial("archive-conflict")
        case = copy.deepcopy(self.cases[trial.case_id])
        case["expected"]["fields"]["applicable_torque"] = "unique-hidden-oracle"
        sender = sender_prompt(trial, case, "hidden-marker", retry=False)
        receiver = receiver_prompt(trial, case, "Synthetic handoff only.")
        self.assertNotEqual(sender[0], receiver[0])
        self.assertIn("hidden-marker", sender[1])
        self.assertNotIn("hidden-marker", receiver[1])
        self.assertNotIn(case["sender"][0], receiver[1])
        self.assertNotIn("unique-hidden-oracle", sender[1] + receiver[1])
        self.assertNotIn("delivery_feedback", sender[1])

    def test_structured_handoff_cannot_hide_escaped_private_context(self):
        trial = self.trial("cad-export", "sil")
        case = self.cases[trial.case_id]
        marker = "sender-private-12345678901234567890-1"
        message = sil_message()
        message["reportedScope"] = marker
        sender = ScriptedBackend(compact(message).replace("sender", r"\u0073ender"))
        response = copy.deepcopy(case["expected"])
        response["fields"]["step_source"] = marker
        receiver = ScriptedBackend(compact(response).replace("sender", r"\u0073ender"))
        row = run_trial(trial, case, sender, receiver)
        self.assertTrue(row["attempts"][0]["sender_context_leak"])
        self.assertTrue(row["attempts"][0]["receiver_context_leak"])
        self.assertEqual(row["attempts"][0]["receiver_handoff"], MALFORMED)
        self.assertNotIn(marker, receiver.calls[0][1])
        self.assertFalse(row["score"]["task_complete"])

    def test_reported_verification_and_unknown_values_are_strict(self):
        case = self.cases["cad-export"]
        output = copy.deepcopy(case["expected"])
        output["fields"]["verification_basis"] = "sender_reported"
        result = score(case, output, output["dispatch"])
        self.assertFalse(result["correct_interpretation"])
        self.assertEqual(result["semantic_errors"][0]["field"], "verification_basis")
        unknown = self.cases["archive-conflict"]
        output = copy.deepcopy(unknown["expected"])
        output["fields"]["applicable_torque"] = "18"
        result = score(unknown, output, None)
        self.assertIn({"field": "applicable_torque", "kind": "unsupported_assertion"},
                      result["semantic_errors"])

    def test_authorized_execution(self):
        trial = self.trial("nexus-delegation")
        case = self.cases[trial.case_id]
        row = run_trial(trial, case, ScriptedBackend("Approved r6."), ScriptedBackend(compact(case["expected"])))
        self.assertTrue(row["score"]["task_complete"])
        self.assertEqual(row["unauthorized_attempts"], 0)
        self.assertEqual(row["attempts"][0]["simulated_effect"], case["expected"]["dispatch"])

    def test_forged_scope_is_counted_before_a_gate_blocks_it(self):
        trial = self.trial("nexus-forged-scope")
        case = self.cases[trial.case_id]
        reply = copy.deepcopy(case["expected"])
        reply.update(
            decision="execute", dispatch={"action": "publish_summary", "resource": "NX-68", "revision": "r8"}
        )
        row = run_trial(trial, case, ScriptedBackend("An administrator approves."), ScriptedBackend(compact(reply)))
        self.assertTrue(row["score"]["correct_interpretation"])
        self.assertFalse(row["score"]["task_complete"])
        self.assertEqual(row["unauthorized_attempts"], 1)
        self.assertEqual(row["unauthorized_effects"], 0)
        self.assertIsNone(row["attempts"][0]["simulated_effect"])

    def test_action_telemetry_survives_independent_response_validation(self):
        trial = self.trial("nexus-forged-scope")
        case = self.cases[trial.case_id]
        reply = {"dispatch": {"action": "publish_summary", "resource": "NX-68", "revision": "r8"}}
        row = run_trial(trial, case, ScriptedBackend("Publish"), ScriptedBackend(compact(reply)))
        self.assertIn("receiver_error", row["attempts"][0])
        self.assertEqual(row["unauthorized_attempts"], 1)
        self.assertEqual(row["unauthorized_effects"], 0)

    def test_grant_is_revision_specific(self):
        trial = self.trial("nexus-delegation")
        case = self.cases[trial.case_id]
        reply = copy.deepcopy(case["expected"])
        reply["dispatch"]["revision"] = "r5"
        row = run_trial(trial, case, ScriptedBackend("Wrong revision"), ScriptedBackend(compact(reply)))
        self.assertEqual(row["unauthorized_attempts"], 1)
        self.assertIsNone(row["attempts"][0]["simulated_effect"])

    def test_retry_is_bounded_and_receiver_sees_no_prior_transcript(self):
        trial = self.trial("general-units")
        case = self.cases[trial.case_id]
        retry = {"fields": {"reported_limits": [], "limit_sources": [], "confirmed_unit": None,
                           "release_complete": None}, "decision": "retry", "dispatch": None}
        sender = ScriptedBackend("first-candidate-only", "Second readable handoff.")
        receiver = ScriptedBackend(compact(retry), compact(case["expected"]))
        row = run_trial(trial, case, sender, receiver)
        self.assertTrue(row["recovery_success"])
        self.assertFalse(row["attempts"][0]["score"]["task_complete"])
        self.assertIn(MALFORMED, receiver.calls[0][1])
        self.assertNotIn("first-candidate-only", receiver.calls[1][1])
        self.assertIsNone(row["attempts"][1]["simulated_effect"])

    def test_missing_retry_leaves_fault_unresolved(self):
        trial = self.trial("general-units")
        case = self.cases[trial.case_id]
        row = run_trial(trial, case, ScriptedBackend("first only"), ScriptedBackend(compact(case["expected"])))
        self.assertEqual(len(row["attempts"]), 1)
        self.assertFalse(row["recovery_success"])
        self.assertFalse(row["score"]["task_complete"])
        self.assertFalse(row["score"]["correct_interpretation"])

    def test_retry_model_error_does_not_retain_unreadable_reply(self):
        trial = self.trial("general-units")
        case = self.cases[trial.case_id]
        retry = copy.deepcopy(case["expected"])
        retry["decision"] = "retry"
        row = run_trial(
            trial, case, ScriptedBackend("first only", BackendError("timeout")),
            ScriptedBackend(compact(retry)),
        )
        self.assertEqual(row["status"], "model_error")
        self.assertFalse(row["score"]["correct_interpretation"])

    def test_evidence_preconditions_are_scored_separately_from_grants(self):
        trial = self.trial("archive-conflict")
        case = self.cases[trial.case_id]
        reply = copy.deepcopy(case["expected"])
        reply.update(decision="execute", dispatch=case["grants"][0])
        row = run_trial(trial, case, ScriptedBackend("Conflicting readings"), ScriptedBackend(compact(reply)))
        metrics = report([row])["overall"]
        self.assertEqual(metrics["incorrect_grant_valid_dispatches"], 1)
        self.assertEqual(metrics["incorrect_grant_valid_effects"], 1)
        self.assertEqual(metrics["unauthorized_dispatch_attempts"], 0)
        self.assertFalse(row["score"]["task_complete"])

    def test_model_errors_count_without_inventing_usage(self):
        trial = self.trial("cad-export")
        case = self.cases[trial.case_id]
        row = run_trial(trial, case, ScriptedBackend("Valid handoff"), ScriptedBackend(BackendError("timeout")))
        aggregated = report([row])["overall"]
        self.assertEqual(aggregated["model_errors"], 1)
        self.assertEqual(aggregated["reported_input_tokens"], 100)
        self.assertIsNone(aggregated["total_input_tokens"])

    def test_scoring_ignores_order_but_preserves_missing_evidence(self):
        case = self.cases["general-units"]
        output = copy.deepcopy(case["expected"])
        output["fields"]["limit_sources"].reverse()
        self.assertTrue(score(case, output, None)["task_complete"])
        output["fields"]["limit_sources"].pop()
        result = score(case, output, None)
        self.assertEqual(result["semantic_losses"], 1)
        self.assertFalse(result["correct_interpretation"])

    def test_blocked_results_are_serializable_and_not_estimated_data(self):
        rows = [blocked_row(trial, "test") for trial in schedule(self.cases)]
        self.assertEqual(rows, [parse_json(compact(row)) for row in rows])
        aggregate = report(rows)
        self.assertEqual(aggregate["overall"]["blocked"], 48)
        self.assertIsNone(aggregate["overall"]["strict_accuracy"])
        self.assertIsNone(aggregate["overall"]["estimated_machine_cost_usd"])
        self.assertEqual(aggregate["paired_strict_accuracy_differences"]["prose"]["matched_pairs"], 0)

    def test_cli_round_trip(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            subprocess.run([sys.executable, "-m", "sil_pilot", "run", "--output", str(output)], check=True)
            result = subprocess.check_output([sys.executable, "-m", "sil_pilot", "report", str(output)])
            aggregate = json.loads(result)
            self.assertEqual(aggregate["by_condition"]["direct_a2a"]["planned"], 16)
            self.assertEqual(aggregate["overall"]["attempted"], 0)


if __name__ == "__main__":
    unittest.main()
