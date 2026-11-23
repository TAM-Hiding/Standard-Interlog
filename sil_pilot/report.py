"""Aggregate actual trials without treating blocked cells as observations."""

from collections import Counter
from statistics import median


def _sum_if_complete(values):
    return sum(values) if values and all(value is not None for value in values) else None


def _timing(values):
    return median(values) if values else None


def summarize(rows, hourly_rate=None):
    attempted = [row for row in rows if row["status"] != "blocked"]
    completed = [row for row in rows if row["status"] == "completed"]
    scores = [row["score"] for row in attempted]
    rounds = [attempt for row in attempted for attempt in row["attempts"]]
    calls = [attempt[role] for attempt in rounds for role in ("sender", "receiver") if role in attempt]
    strict = sum(score["task_complete"] for score in scores)
    wall = _sum_if_complete([row["elapsed_seconds"] for row in attempted])
    recoverable = [row["recovery_success"] for row in attempted if row["recovery_success"] is not None]
    pairs = [attempt for attempt in rounds if "score" in attempt]
    result = {
        "planned": len(rows),
        "attempted": len(attempted),
        "completed": len(completed),
        "blocked": len(rows) - len(attempted),
        "model_errors": len(attempted) - len(completed),
        "first_attempt_strict_successes": sum(
            row["attempts"][0].get("score", {}).get("task_complete", False) for row in attempted
        ),
        "strict_successes": strict,
        "strict_accuracy": strict / len(attempted) if attempted else None,
        "correct_interpretation_rate": (
            sum(score["correct_interpretation"] for score in scores) / len(attempted)
            if attempted else None
        ),
        "semantic_losses": sum(score["semantic_losses"] for score in scores),
        "semantic_fields": sum(score["semantic_fields"] for score in scores),
        "semantic_errors": dict(Counter(error["kind"] for score in scores for error in score["semantic_errors"])),
        "unauthorized_dispatch_attempts": sum(row["unauthorized_attempts"] for row in attempted),
        "unauthorized_effects": sum(row["unauthorized_effects"] for row in attempted),
        "incorrect_grant_valid_dispatches": sum(attempt["incorrect_grant_valid_dispatch"] for attempt in pairs),
        "incorrect_grant_valid_effects": sum(attempt["incorrect_grant_valid_effect"] for attempt in pairs),
        "unreadable_dispatch_attempts": sum(attempt["unreadable_dispatch_attempt"] for attempt in pairs),
        "context_leaks": sum(
            bool(attempt.get("sender_context_leak")) + bool(attempt.get("receiver_context_leak"))
            for attempt in rounds
        ),
        "handoff_validation_failures": sum(bool(attempt.get("handoff_error")) for attempt in rounds),
        "receiver_validation_failures": sum(bool(attempt.get("receiver_error")) for attempt in rounds),
        "recovery_cases": len(recoverable),
        "recovery_successes": sum(recoverable),
        "reported_model_calls": len(calls),
        "elapsed_seconds": wall,
        "median_trial_seconds": _timing([row["elapsed_seconds"] for row in attempted]),
        "median_encode_seconds": _timing([
            attempt["encode_seconds"] for attempt in rounds if "encode_seconds" in attempt
        ]),
        "median_decode_seconds": _timing([
            attempt["decode_seconds"] for attempt in rounds if attempt.get("decode_seconds") is not None
        ]),
        "machine_seconds_per_strict_success": wall / strict if strict else None,
        "estimated_machine_cost_usd": (
            wall * hourly_rate / 3600 if wall is not None and hourly_rate is not None else None
        ),
    }
    # A failing worker may consume resources without returning usage. Preserve that missingness.
    for name in ("input_tokens", "output_tokens", "cpu_seconds"):
        result[f"reported_{name}"] = _sum_if_complete([call[name] for call in calls])
        result[f"total_{name}"] = result[f"reported_{name}"] if result["model_errors"] == 0 else None
    return result


def paired_differences(rows):
    paired = {}
    for row in rows:
        if row["status"] != "blocked":
            key = (row["case_id"], row["sender_family"], row["receiver_family"])
            paired.setdefault(key, {})[row["condition"]] = row["score"]["task_complete"]
    result = {}
    for control in ("prose", "direct_a2a"):
        differences = [int(pair["sil"]) - int(pair[control])
                       for pair in paired.values() if {"sil", control} <= pair.keys()]
        result[control] = {
            "matched_pairs": len(differences),
            "sil_minus_control_accuracy": sum(differences) / len(differences) if differences else None,
            "sil_only_successes": differences.count(1),
            "control_only_successes": differences.count(-1),
        }
    return result


def report(rows, hourly_rate=None):
    def group(key):
        groups = {}
        for row in rows:
            groups.setdefault(key(row), []).append(row)
        return {name: summarize(groups[name], hourly_rate) for name in sorted(groups)}

    return {
        "overall": summarize(rows, hourly_rate),
        "by_condition": group(lambda row: row["condition"]),
        "by_domain_and_condition": group(lambda row: f'{row["domain"]}/{row["condition"]}'),
        "by_direction_and_condition": group(
            lambda row: f'{row["sender_family"]}->{row["receiver_family"]}/{row["condition"]}'
        ),
        "paired_strict_accuracy_differences": paired_differences(rows),
    }
