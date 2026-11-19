from extract_bench.inference.pipelines import get_pipeline

import idp.bench


def test_unigpt_pipelines_are_registered():
    for name, model in idp.bench.UNIGPT_ONESHOT.items():
        spec = get_pipeline(name)
        assert spec.provider_name == "vllm_extract"
        assert spec.config["model"] == model
        assert spec.config["api_key_env"] == "UNIGPT_API_KEY"
