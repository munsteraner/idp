"""`idp-bench`: the extract-bench CLI with this project's pipelines registered."""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def _models() -> None:
    """Print the models the uniGPT key can reach, and the key's budget info."""
    from dotenv import load_dotenv

    from idp.bench import UNIGPT_URL

    load_dotenv(".env")
    key = os.environ.get("UNIGPT_API_KEY", "")
    if not key:
        sys.exit("UNIGPT_API_KEY is empty; fill it in .env")
    for path in ("/v1/models", "/key/info"):
        req = urllib.request.Request(UNIGPT_URL + path, headers={"Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception as e:  # report and continue with the next endpoint
            print(f"{path}: {e}")
            continue
        if path == "/v1/models":
            print("models:", *sorted(m["id"] for m in data.get("data", [])), sep="\n  ")
        else:
            info = data.get("info", data)
            keep = {k: v for k, v in info.items() if "key" not in k.lower() and "token" != k.lower()}
            print("key info:", json.dumps(keep, indent=2, default=str)[:3000])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "models":
        _models()
        return
    import idp.bench  # noqa: F401  (registers pipelines)
    from extract_bench.cli import main as bench_main

    bench_main()


if __name__ == "__main__":
    main()
