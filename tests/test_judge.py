from types import SimpleNamespace

from backend import judge


def test_model_judge_is_explicitly_separate_from_human_scores(monkeypatch):
    class Model:
        def bind(self, **kwargs):
            return self

        def invoke(self, messages):
            assert "不可信数据" in messages[0][1]
            return SimpleNamespace(content='{"score":0.5,"rationale":"关键步骤不完整"}')

    monkeypatch.setattr(judge, "model", lambda: Model())
    monkeypatch.setattr(judge.settings, "judge_model", None)
    result = judge.judge("question", "reference", "answer")
    assert result["score"] == 0.5 and result["method"] == "LLM-as-Judge"
    assert result["independent_model"] is False
    assert "accuracy" not in result
