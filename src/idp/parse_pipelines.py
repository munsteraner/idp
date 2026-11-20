"""Pipelines this project adds to the ParseBench harness, through its public extension API.

Merged pipelines (built from cached parse outputs, see ``idp.merge_decorations``) have no provider of
their own. The layout scorer picks its adapter by a result's provider, so each merge names the provider
whose layout boxes it carries. The scorer itself is unchanged.
"""

from __future__ import annotations

from parse_bench.extensions import register_pipeline_resolver
from parse_bench.schemas.pipeline import PipelineSpec
from parse_bench.schemas.product import ProductType

# Merged pipeline -> provider of the layout boxes it keeps (the base parser's).
MERGES: dict[str, str] = {
    "merge_decor": "lightonocr3",
}


def _resolve(name: str) -> PipelineSpec | None:
    provider = MERGES.get(name)
    if provider is None:
        return None
    return PipelineSpec(pipeline_name=name, provider_name=provider, product_type=ProductType.PARSE, config={})


register_pipeline_resolver(_resolve)
