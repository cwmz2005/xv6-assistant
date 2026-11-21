from types import SimpleNamespace

from backend.chat.conversation import retrieval_query


def test_followup_preserves_named_topic():
    history = [SimpleNamespace(role="user", content="walkaddr 的作用是什么？")]
    assert "walkaddr" in retrieval_query("它在哪里定义？", history)
    assert retrieval_query("Explain scheduler", history) == "Explain scheduler"


def test_history_context_is_bounded():
    history = [SimpleNamespace(role="user", content="x" * 4000)] * 20
    assert len(retrieval_query("What does it return?", history)) < 3100
