from types import SimpleNamespace

from backend import generation


def test_bounded_search_answers_every_tool_call_and_sanitizes_citations(monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage

    known = "a" * 64
    unknown = "b" * 64

    class Model:
        def bind_tools(self, schema):
            return self

        def invoke(self, messages):
            if any(isinstance(m, ToolMessage) for m in messages):
                assert sum(isinstance(m, ToolMessage) for m in messages) == 4
                return AIMessage(content=f"answer [{known}] [{unknown}]")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "knowledge_search",
                        "args": {"query": "walkaddr"},
                        "id": str(i),
                        "type": "tool_call",
                    }
                    for i in range(4)
                ],
            )

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    calls = []

    def search(query):
        calls.append(query)
        return {"results": [{"id": known, "text": "evidence", "location": {}}]}

    answer, citations, logs = generation.generate(
        "question", [], [], search_tool=search
    )
    assert len(calls) == 1 and len(logs) == 1
    assert citations[0]["id"] == known
    assert unknown not in answer


def test_baseline_does_not_claim_evidence(monkeypatch):
    class Model:
        def invoke(self, messages):
            assert "当前未检索知识库" in messages[0].content
            return SimpleNamespace(content="baseline answer")

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    assert generation.generate("question", [], [], rag=False)[1] == []


def test_default_allows_multiple_distinct_searches(monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage

    class Model:
        def bind_tools(self, schema):
            return self

        def invoke(self, messages):
            count = sum(isinstance(m, ToolMessage) for m in messages)
            if count < 2:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "knowledge_search",
                            "args": {"query": f"file-{count}"},
                            "id": str(count),
                            "type": "tool_call",
                        }
                    ],
                )
            return AIMessage(content="Evidence collected")

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    calls = []

    def search(query):
        calls.append(query)
        return {"results": [{"id": query, "text": query, "location": {}}]}

    _, _, logs = generation.generate("cross file question", [], [], search_tool=search)
    assert calls == ["file-0", "file-1"] and len(logs) == 2


def test_unique_short_citation_resolves_to_real_evidence(monkeypatch):
    from langchain_core.messages import AIMessage

    cid = "1234abcd" + "a" * 56

    class Model:
        def invoke(self, messages):
            return AIMessage(content="claim [1234abcd]")

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    answer, citations, _ = generation.generate("question", [], [{"id": cid}])
    assert "[" + cid + "]" in answer and citations == [{"id": cid}]


def test_trace_and_details_are_streamed_and_persisted(monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage

    class Model:
        def bind_tools(self, schema):
            return self

        def invoke(self, messages):
            if any(isinstance(m, ToolMessage) for m in messages):
                return AIMessage(content="answer")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "knowledge_search",
                        "args": {"query": "copyin"},
                        "id": "1",
                        "type": "tool_call",
                    }
                ],
            )

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    tool_events = []
    detail_events = []
    streamed = []
    trace = []

    def search(query):
        tool_events.append(query)
        return {
            "results": [
                {
                    "id": "a" * 64,
                    "text": "evidence",
                    "location": {"path": "kernel/vm.c", "start_line": 1},
                    "scores": {"rrf": 0.5},
                }
            ],
            "candidate_scores": [
                {"id": "a" * 64, "ranks": {"dense": 1}, "scores": {"rrf": 0.5}}
            ],
            "retrieval_ms": 3.0,
        }

    trace_token = generation.trace_sink.set(streamed.append)
    detail_token = generation.detail_sink.set(detail_events.append)
    try:
        with generation.collect_details() as collected:
            answer, citations, _ = generation.generate(
                "question", [], [], search_tool=search, trace=trace
            )
    finally:
        generation.detail_sink.reset(detail_token)
        generation.trace_sink.reset(trace_token)

    assert answer == "answer" and citations == []
    assert tool_events == ["copyin"]
    assert [step["type"] for step in trace] == ["search", "answer"]
    assert trace[0]["status"] == "done" and trace[0]["added"] == 1
    assert [step["status"] for step in streamed if step["type"] == "search"] == [
        "running",
        "done",
    ]
    assert [event["type"] for event in detail_events] == [
        "system_prompt",
        "prompt",
        "tool_call",
        "tool_result",
        "prompt",
        "final_context",
    ]
    assert collected == detail_events
    assert "xv6" in detail_events[0]["text"]
    assert detail_events[1]["messages"][0]["type"] == "system"
    assert detail_events[1]["messages"][-1]["type"] == "human"
    assert detail_events[3]["results"][0]["id"] == "a" * 64
    assert detail_events[3]["candidate_scores"][0]["ranks"] == {"dense": 1}
    assert detail_events[4]["messages"][-1]["type"] == "tool"


def test_path_regex_is_forwarded_and_recorded(monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage

    schema_holder = {}
    prompts = []

    class Model:
        def bind_tools(self, schema):
            schema_holder.update(schema[0]["function"])
            return self

        def invoke(self, messages):
            prompts.append(messages[0].content)
            if any(isinstance(m, ToolMessage) for m in messages):
                return AIMessage(content="answer")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "knowledge_search",
                        "args": {
                            "query": "uvmalloc kalloc memset",
                            "path_regex": r"kernel/.*\.c$",
                        },
                        "id": "1",
                        "type": "tool_call",
                    }
                ],
            )

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    calls = []

    def search(query, path_regex=None):
        calls.append((query, path_regex))
        return {
            "results": [
                {
                    "id": "a" * 64,
                    "text": "evidence",
                    "location": {"path": "kernel/vm.c", "start_line": 1},
                }
            ],
            "candidate_scores": [],
            "retrieval_ms": 1.0,
        }

    streamed = []
    details = []
    trace = []
    trace_token = generation.trace_sink.set(streamed.append)
    detail_token = generation.detail_sink.set(details.append)
    try:
        answer, _, logs = generation.generate(
            "question", [], [], search_tool=search, trace=trace
        )
    finally:
        generation.detail_sink.reset(detail_token)
        generation.trace_sink.reset(trace_token)

    properties = schema_holder["parameters"]["properties"]
    assert "path_regex" in properties
    assert "path_regex" in prompts[0] and "2–5" in prompts[0]
    assert calls == [("uvmalloc kalloc memset", r"kernel/.*\.c$")]
    assert trace[0]["path_regex"] == r"kernel/.*\.c$"
    assert logs[0]["path_regex"] == r"kernel/.*\.c$"
    tool_events = [e for e in details if e["type"] in ("tool_call", "tool_result")]
    assert all(e["path_regex"] == r"kernel/.*\.c$" for e in tool_events)
    assert answer == "answer"


def test_invalid_path_regex_is_rejected_without_search(monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage

    class Model:
        def bind_tools(self, schema):
            return self

        def invoke(self, messages):
            if any(isinstance(m, ToolMessage) for m in messages):
                return AIMessage(content="answer")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "knowledge_search",
                        "args": {"query": "kalloc", "path_regex": "["},
                        "id": "1",
                        "type": "tool_call",
                    }
                ],
            )

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    calls = []
    trace = []

    def search(query, path_regex=None):
        calls.append(query)
        return {"results": []}

    answer, _, logs = generation.generate(
        "question", [], [], search_tool=search, trace=trace
    )
    assert answer == "answer" and logs == [] and calls == []
    assert trace[0]["status"] == "skipped"
    assert "path_regex" in trace[0]["reason"]


def test_truncated_response_is_explicit(monkeypatch):
    from langchain_core.messages import AIMessage

    class Model:
        def invoke(self, messages):
            return AIMessage(
                content="partial", response_metadata={"finish_reason": "length"}
            )

    monkeypatch.setattr(generation.client, "model", lambda: Model())
    assert "回答尚未完成" in generation.generate("question", [], [], False)[0]
