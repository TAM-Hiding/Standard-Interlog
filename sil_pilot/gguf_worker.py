"""One request per process. No service, history, tooling or external I/O."""

from contextlib import closing
import importlib.metadata
import json
import sys
from time import process_time

from .backend import MAX_OUTPUT_TOKENS, SEED


def main():
    start = process_time()
    try:
        from llama_cpp import Llama

        request = json.load(sys.stdin)
        settings = {
            "n_ctx": 4096,
            "n_threads": 4,
            "n_gpu_layers": 0,
            "seed": SEED,
            "verbose": False,
        }
        with closing(Llama(
            model_path=request["path"], chat_format=request["chat_format"],
            vocab_only="prompt" not in request, **settings,
        )) as model:
            if "prompt" not in request:
                metadata = model.metadata
                answer = {
                    "architecture": metadata.get("general.architecture", ""),
                    "name": metadata.get("general.name", ""),
                    "file_type": metadata.get("general.file_type"),
                    "runtime_version": importlib.metadata.version("llama-cpp-python"),
                    "context_tokens": settings["n_ctx"],
                    "threads": settings["n_threads"],
                    "gpu_layers": settings["n_gpu_layers"],
                }
            else:
                response = model.create_chat_completion(
                    messages=[
                        {"role": "system", "content": request["system"]},
                        {"role": "user", "content": request["prompt"]},
                    ],
                    temperature=0, max_tokens=MAX_OUTPUT_TOKENS, seed=SEED,
                )
                choice = response["choices"][0]
                answer = {
                    "text": choice["message"].get("content") or "",
                    "input_tokens": response["usage"]["prompt_tokens"],
                    "output_tokens": response["usage"]["completion_tokens"],
                    "cpu_seconds": process_time() - start,
                    "finish_reason": choice.get("finish_reason"),
                }
    except Exception as error:
        # Trace errors without recording local paths or library diagnostics.
        answer = {"error": f"local GGUF worker failed: {type(error).__name__}"}
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
