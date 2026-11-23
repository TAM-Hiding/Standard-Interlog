"""Fresh, local model calls with an injectable interface for offline tests."""

from dataclasses import dataclass
from hashlib import file_digest
import importlib.util
import json
import subprocess
import sys
from typing import Protocol

from .formats import compact


SEED = 19
MAX_OUTPUT_TOKENS = 768
CALL_TIMEOUT = 90
ARCHITECTURES = {"qwen": {"qwen2", "qwen3"}, "llama": {"llama"}}


class BackendError(RuntimeError):
    pass


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cpu_seconds: float | None = None
    finish_reason: str | None = None


class Backend(Protocol):
    def complete(self, system: str, prompt: str) -> Completion: ...


class LocalGGUF:
    def __init__(self, config, base):
        self.path = (base / config["path"]).resolve()
        self.family = config["family"]
        if self.family not in ARCHITECTURES:
            raise BackendError("pilot backend supports a Qwen and a Llama checkpoint")
        if not self.path.is_file() or self.path.suffix.lower() != ".gguf":
            raise BackendError(f"local GGUF unavailable for {self.family}")
        if not all(isinstance(config.get(key), str) and config[key].strip()
                   for key in ("model_id", "revision", "source", "chat_format")):
            raise BackendError("supply model ID, revision, source and chat format")
        with self.path.open("rb") as model:
            digest = file_digest(model, "sha256").hexdigest()
        if digest != config.get("sha256"):
            raise BackendError(f"local GGUF checksum mismatch for {self.family}")
        self.options = {"path": str(self.path), "chat_format": config["chat_format"]}
        meta = self._invoke({})
        if meta["architecture"] not in ARCHITECTURES[self.family]:
            raise BackendError(f"unexpected GGUF architecture for {self.family}")
        if self.family not in meta["name"].casefold():
            raise BackendError(f"GGUF general.name does not identify {self.family}")
        self.metadata = {
            key: config[key] for key in ("family", "model_id", "revision", "source", "chat_format")
        }
        self.metadata.update(meta, sha256=digest)

    def _invoke(self, request):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "sil_pilot.gguf_worker"],
                input=compact(self.options | request),
                text=True, encoding="utf-8", capture_output=True,
                timeout=CALL_TIMEOUT, check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise BackendError("local model call timed out") from error
        if result.returncode:
            raise BackendError(f"local GGUF worker exited with status {result.returncode}")
        try:
            data = json.loads(result.stdout)
        except ValueError as error:
            raise BackendError("local GGUF worker returned invalid JSON") from error
        if "error" in data:
            raise BackendError(data["error"])
        return data

    def complete(self, system, prompt):
        return Completion(**self._invoke({"system": system, "prompt": prompt}))


def load_pair(path):
    try:
        if importlib.util.find_spec("llama_cpp") is None:
            raise BackendError("optional llama-cpp-python runtime unavailable")
        config = json.loads(path.read_text())
        if not isinstance(config, list) or len(config) != 2:
            raise BackendError("supply exactly two local model definitions")
        if {item["family"] for item in config} != set(ARCHITECTURES):
            raise BackendError("supply distinct, supported Qwen and Llama families")
        pair = [LocalGGUF(item, path.parent) for item in config]
        if pair[0].metadata["sha256"] == pair[1].metadata["sha256"]:
            raise BackendError("pilot requires distinct local checkpoints")
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise BackendError(f"cannot load local model configuration ({type(error).__name__})") from error
    return pair
