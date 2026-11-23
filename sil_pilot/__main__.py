"""Offline CLI. Without an explicit verified pair, emit the blocked pilot matrix."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
from time import perf_counter

from .backend import BackendError, CALL_TIMEOUT, MAX_OUTPUT_TOKENS, SEED, load_pair
from .report import report
from .trials import FIXTURES, ORDER_SEED, blocked_row, fixtures, run_trial, schedule


def run(args):
    cases = fixtures()
    pair = {}
    reason = "no verified local model pair configured"
    started = perf_counter()
    if args.models:
        try:
            pair = {backend.family: backend for backend in load_pair(args.models)}
        except BackendError as error:
            reason = str(error)
    root = Path(__file__).resolve().parents[1]
    frozen_inputs = sorted((root / "sil_pilot").glob("*.py")) + [
        FIXTURES, root / "schemas/sil-experimental.schema.json", root / "requirements.txt",
    ]
    manifest = {
        "mode": "local_gguf" if pair else "blocked",
        "backends": {family: backend.metadata for family, backend in pair.items()},
        "reason": None if pair else reason,
        "platform": platform.platform() if pair else None,
        "python": platform.python_version() if pair else None,
        "model_seed": SEED,
        "temperature": 0,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "call_timeout_seconds": CALL_TIMEOUT,
        "preflight_seconds": perf_counter() - started if args.models else None,
        "hourly_machine_rate_usd": args.hourly_rate,
        "api_spend_usd": 0,
        "order_seed": ORDER_SEED,
        "inputs_sha256": {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
                          for path in frozen_inputs},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (args.output / "trials.jsonl").open("w", encoding="utf-8") as raw:
        for trial in schedule(cases):
            row = (
                run_trial(trial, cases[trial.case_id], pair[trial.sender_family], pair[trial.receiver_family])
                if pair else blocked_row(trial, reason)
            )
            raw.write(json.dumps(row, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n")
            raw.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--models", type=Path)
    run_parser.add_argument("--hourly-rate", type=float, help="optional local USD per machine-hour estimate")
    summarize = commands.add_parser("report")
    summarize.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        if args.hourly_rate is not None and (args.hourly_rate < 0 or not math.isfinite(args.hourly_rate)):
            parser.error("hourly rate must be a finite, nonnegative estimate")
        run(args)
    else:
        manifest = json.loads((args.directory / "manifest.json").read_text())
        rows = [json.loads(line) for line in (args.directory / "trials.jsonl").read_text().splitlines()]
        print(json.dumps(report(rows, manifest["hourly_machine_rate_usd"]), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
