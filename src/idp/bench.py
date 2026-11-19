"""Pipelines this project adds to the official ExtractBench harness.

Importing this module registers them. Run them with `idp-bench run <name>`,
which is the `extract-bench` CLI with these registrations loaded.

The scorer, the dataset loader and the reports are the harness's own. Nothing
here may reshape model output before it is scored.
"""
from __future__ import annotations

from extract_bench.extensions import register_pipeline
from extract_bench.inference.limits import EXTRACT_HARD_TIMEOUT_S
from extract_bench.schemas.pipeline import PipelineSpec
from extract_bench.schemas.product import ProductType

import idp.streaming  # noqa: F401  (registers the streaming provider)

UNIGPT_URL = "https://gpt.uni-muenster.de"  # the provider appends /v1

# One-shot reference baselines on the university endpoint: page images in, JSON
# out, same prompt and settings as the harness's self-hosted vLLM rows (only the
# transport streams, see idp.streaming), so the
# scores are comparable with the published leaderboard. Model names are the ones
# the uniGPT docs list; `idp-bench models` shows what the key can reach.
UNIGPT_ONESHOT = {
    "unigpt_deepseek_v4_flash_oneshot": "DeepSeek-V4-Flash",
    "unigpt_qwen3_8_27b_oneshot": "Qwen3.8-27B",
}


def _register() -> None:
    for name, model in UNIGPT_ONESHOT.items():
        register_pipeline(
            PipelineSpec(
                pipeline_name=name,
                provider_name="openai_compat_stream_extract",
                product_type=ProductType.EXTRACT,
                config={
                    "server_url": UNIGPT_URL,
                    "api_key_env": "UNIGPT_API_KEY",
                    "model": model,
                    "additional_properties_false": True,
                    "max_tokens": 32768,
                    "structured_output": False,  # json_object mode, as the leaderboard rows
                    "timeout_s": EXTRACT_HARD_TIMEOUT_S,
                },
            )
        )


_register()
