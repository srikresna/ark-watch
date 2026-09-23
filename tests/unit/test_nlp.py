from arkwatch.fetchers import nlp


class _Response:
    def __init__(self, text):
        self.text = text

    def json(self):
        raise nlp.requests.exceptions.JSONDecodeError("extra", self.text, 1)


def test_custom_v1_base_url_resolves_chat_completions(monkeypatch):
    monkeypatch.setenv("NLP_PROVIDER", "custom")
    monkeypatch.setenv("NLP_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NLP_API_KEY", "test")
    assert nlp._config()["endpoint"] == "https://example.test/v1/chat/completions"


def test_custom_full_endpoint_is_unchanged(monkeypatch):
    monkeypatch.setenv("NLP_PROVIDER", "custom")
    monkeypatch.setenv("NLP_BASE_URL", "https://example.test/v1/chat/completions")
    monkeypatch.setenv("NLP_API_KEY", "test")
    assert nlp._config()["endpoint"] == "https://example.test/v1/chat/completions"


def test_openai_content_accepts_json_before_sse_done_marker():
    raw = '{"choices":[{"message":{"content":"ok"}}]}data: [DONE]'
    assert nlp._openai_content(_Response(raw)) == "ok"
