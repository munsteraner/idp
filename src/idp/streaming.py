"""Streaming variant of the harness's OpenAI-compatible extraction provider.

The uniGPT gateway drops a non-streaming request after 240 seconds without a
response (measured 2026-11-19), which kills every document with a long output.
Streaming keeps the connection alive. Prompt, images, decoding settings and
output handling are the harness's own and unchanged, so scores stay comparable.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from extract_bench.extensions import register_provider
from extract_bench.inference.providers.extract.vllm_extract import VLLMExtractProvider


class _StreamingCompletions:
    def __init__(self, completions: Any):
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        stream = self._completions.create(
            **kwargs, stream=True, stream_options={"include_usage": True}
        )
        parts: list[str] = []
        finish_reason = None
        usage = None
        for chunk in stream:
            if getattr(chunk, "usage", None) is not None:
                usage = chunk.usage
            for choice in chunk.choices or []:
                if choice.delta is not None and choice.delta.content:
                    parts.append(choice.delta.content)
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        message = SimpleNamespace(content="".join(parts))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
            usage=usage,
        )


class _StreamingClient:
    def __init__(self, client: Any):
        self.chat = SimpleNamespace(completions=_StreamingCompletions(client.chat.completions))


@register_provider("openai_compat_stream_extract")
class StreamingExtractProvider(VLLMExtractProvider):
    def __init__(self, provider_name: str, base_config: dict[str, Any] | None = None):
        super().__init__(provider_name, base_config)
        self._client = _StreamingClient(self._client)
