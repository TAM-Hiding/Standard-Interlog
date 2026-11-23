"""Model-facing payload adapters and the common offline carrier."""

import json
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator


CONDITIONS = ("prose", "sil", "direct_a2a")
DOMAIN_REPORTS = {
    "hero_cad": "manufacturingReport",
    "archive": "recordSummary",
    "tam_nexus": "delegationReview",
    "general": "handoffDetails",
}
MAX_BYTES = 16_384
MALFORMED = "[Handoff unreadable: carrier frame truncated]"


class InvalidMessage(ValueError):
    pass


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InvalidMessage(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _constant(value):
    raise InvalidMessage(f"invalid JSON constant: {value}")


def _check_text(text):
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise InvalidMessage("message is not valid UTF-8") from error
    if size > MAX_BYTES:
        raise InvalidMessage("message exceeds byte limit")


def parse_json(text):
    _check_text(text)
    try:
        value = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
        # Also reject escaped lone surrogates, float overflow and excessive nesting.
        _check_text(compact(value))
    except (ValueError, RecursionError) as error:
        raise InvalidMessage(str(error)) from error
    return value


def validate(value, schema):
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error:
        path = ".".join(map(str, error.absolute_path)) or "root"
        raise InvalidMessage(f"{path}: {error.validator}")


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


STRING = {"type": "string", "minLength": 1, "maxLength": 600}
NULLABLE = {"anyOf": [STRING, {"type": "null"}]}
SIL_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "schemas/sil-experimental.schema.json").read_text()
)


def report_fields(fixture):
    fields = {}
    for name, field in fixture["fields"].items():
        if field.get("multiple"):
            fields[name] = {"type": "array", "items": STRING, "uniqueItems": True}
        elif "choices" in field:
            fields[name] = {"enum": [*field["choices"], None]}
        else:
            fields[name] = NULLABLE
    return fields


def direct_schema(fixture):
    return object_schema({
        DOMAIN_REPORTS[fixture["domain"]]: object_schema(report_fields(fixture)),
        "requestedWork": NULLABLE,
        "completedWork": {"type": "array", "items": STRING},
        "limitations": {"type": "array", "items": STRING},
        "scopeAsReported": NULLABLE,
        "sourceNotes": {"type": "array", "items": STRING},
    })


def guide(condition, fixture):
    if condition == "prose":
        return "Handoff format: concise ordinary prose, typically with a short heading or bullets."
    if condition == "sil":
        return (
            "Handoff format: bare JSON with profile sil-experiment/0. Handoff schema:\n"
            + compact(SIL_SCHEMA)
        )
    return (
        "Handoff format: bare JSON domain report carried as native A2A Part.data. "
        "The report keeps conflicting readings separately attributed in sourceNotes and qualifies "
        "reported scope, uncertain claims and outcome limits. It uses null for unknown "
        "singular values and [] for empty lists. Field schema:\n"
        + compact(direct_schema(fixture))
    )


def deliver(condition, fixture, output, message_id):
    """Validate native payloads and round-trip the same A2A Message subset in memory."""
    started = perf_counter()
    try:
        if condition == "prose":
            _check_text(output)
            if not output.strip() or "\0" in output:
                raise InvalidMessage("empty, oversized or invalid prose")
            part = {"text": output}
        else:
            value = parse_json(output)
            validate(value, SIL_SCHEMA if condition == "sil" else direct_schema(fixture))
            part = {"data": value}

        wire = compact({
            "messageId": message_id,
            "role": "ROLE_USER",
            "parts": [part],
        })
        encoded = perf_counter()
        delivered = json.loads(wire)["parts"][0]
        visible = delivered["text"] if condition == "prose" else compact(delivered["data"])
        return wire, visible, None, encoded - started, perf_counter() - encoded
    except InvalidMessage as error:
        return None, MALFORMED, str(error), perf_counter() - started, None
