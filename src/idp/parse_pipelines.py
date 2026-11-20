"""Pipelines this project adds to the ParseBench harness, through its public extension API.

Merged pipelines (built from cached parse outputs, see ``idp.merge_decorations``) have no provider of
their own. The layout scorer picks its adapter by a result's provider, so each merge names the provider
whose layout boxes it carries. The scorer itself is unchanged.
"""

from __future__ import annotations

from parse_bench.extensions import register_pipeline, register_pipeline_resolver
from parse_bench.inference.pipelines import get_pipeline
from parse_bench.schemas.pipeline import PipelineSpec
from parse_bench.schemas.product import ProductType

# Merged pipeline -> provider of the layout boxes it keeps (the base parser's).
MERGES: dict[str, str] = {
    "merge_decor": "lightonocr3",
    "merge_trunc": "lightonocr3",
    "merge_v2": "lightonocr3",
    "merge_corner": "lightonocr3",
    "merge_v3": "lightonocr3",
    "merge_v2_long": "lightonocr3",
}


def _resolve(name: str) -> PipelineSpec | None:
    provider = MERGES.get(name)
    if provider is None:
        return None
    return PipelineSpec(pipeline_name=name, provider_name=provider, product_type=ProductType.PARSE, config={})


register_pipeline_resolver(_resolve)


def _register_variants() -> None:
    """Variants of harness pipelines with changed request settings (IDEAS.md idea 5)."""
    base = get_pipeline("lightonocr3_4b_vllm")
    # Same model, prompt and rendering; output budget 28,672 instead of 12,288 tokens, for pages the
    # harness setting cuts off. The server needs --max-model-len 36864 (jobs/bench_vllm.sh).
    register_pipeline(
        PipelineSpec(
            pipeline_name="lightonocr3_4b_vllm_long",
            provider_name=base.provider_name,
            product_type=base.product_type,
            config={**base.config, "max_tokens": 28672, "timeout": 3000},
            per_file_timeout=3600,
        )
    )


_register_variants()
