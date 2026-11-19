from extract_bench.inference.pipelines import get_pipeline

import idp.bench


def test_unigpt_pipelines_are_registered():
    for name, model in idp.bench.UNIGPT_ONESHOT.items():
        spec = get_pipeline(name)
        assert spec.provider_name == "openai_compat_stream_extract"
        assert spec.config["model"] == model
        assert spec.config["api_key_env"] == "UNIGPT_API_KEY"


def test_streaming_wrapper_reassembles_chunks():
    from types import SimpleNamespace as NS

    from idp.streaming import _StreamingCompletions

    def chunk(text=None, finish=None, usage=None):
        choices = [] if text is None and finish is None else [
            NS(delta=NS(content=text), finish_reason=finish)
        ]
        return NS(choices=choices, usage=usage)

    class Fake:
        def create(self, **kw):
            assert kw["stream"] is True and kw["model"] == "m"
            return iter([chunk('{"a"'), chunk(": 1}"), chunk(finish="stop"),
                         chunk(usage=NS(prompt_tokens=3, completion_tokens=2))])

    r = _StreamingCompletions(Fake()).create(model="m")
    assert r.choices[0].message.content == '{"a": 1}'
    assert r.choices[0].finish_reason == "stop"
    assert r.usage.completion_tokens == 2
