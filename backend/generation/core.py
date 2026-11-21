"""Generation orchestration: prompt assembly, tool rounds and finalization."""

from . import client as client_module
from .citations import finalize_answer
from .events import (
    StreamState,
    emit_detail,
    emit_trace,
    generation_info,
    reasoning_state,
)
from .formatting import snapshot_messages
from .prompts import build_prompt, initial_messages
from .tools import SearchToolRunner, search_tool_schema


class GenerationSession:
    """Holds state for one user turn and runs the optional tool loop."""

    def __init__(
        self,
        question,
        history,
        evidence,
        rag=True,
        search_tool=None,
        max_search_calls=None,
        trace=None,
        versions=None,
    ):
        generation_info.set(None)
        self.question = question
        self.history = history
        self.evidence = evidence
        self.rag = rag
        self.search_tool = search_tool
        self.max_search_calls = max_search_calls
        self.versions = versions or []
        self.trace = [] if trace is None else trace
        self.state = StreamState()
        reasoning_state.set(self.state)
        self.client = client_module.model()
        self.prompt = build_prompt(rag, tools_enabled=bool(search_tool))
        self.messages = initial_messages(self.prompt, question, history, evidence)
        emit_detail(
            {
                "id": "system-prompt",
                "type": "system_prompt",
                "rag": rag,
                "text": self.prompt,
            }
        )
        self.round_number = 0
        self.tool_log = []

    def _invoke(self, runnable):
        self.round_number += 1
        step_id = f"thinking-{self.round_number}"
        self.state.begin(step_id)
        emit_detail(
            {
                "id": f"prompt-{self.round_number}",
                "type": "prompt",
                "round": self.round_number,
                "rag": self.rag,
                "messages": snapshot_messages(self.messages),
            }
        )
        response = runnable.invoke(self.messages)
        text = self.state.text
        if not text:
            extra = getattr(response, "additional_kwargs", None) or {}
            reasoning = extra.get("reasoning_content")
            if isinstance(reasoning, str):
                text = reasoning
        if getattr(response, "tool_calls", None):
            content = response.content
            if isinstance(content, str) and content.strip():
                text = (
                    f"{text.strip()}\n\n{content.strip()}" if text.strip() else content
                )
        if text.strip():
            step = {
                "id": step_id,
                "type": "thinking",
                "status": "done",
                "text": text.strip(),
            }
            self.trace.append(step)
            emit_trace(step)
        return response

    def _run_with_tools(self):
        from langchain_core.messages import ToolMessage

        runner = SearchToolRunner(
            self.search_tool,
            self.max_search_calls,
            self.evidence,
            self.trace,
            versions=self.versions,
        )
        tool_client = self.client.bind_tools([search_tool_schema(self.versions)])
        response = self._invoke(tool_client)
        while response.tool_calls:
            self.messages.append(response)
            runner.begin_round()
            for index, call in enumerate(response.tool_calls):
                content = runner.handle(call, self.round_number, index)
                self.messages.append(
                    ToolMessage(content=content, tool_call_id=call["id"])
                )
            runner.end_round()
            if runner.should_stop():
                response = self._invoke(self.client)
                break
            response = self._invoke(tool_client)
        self.tool_log = runner.tool_log
        return response

    def _finalize(self, response):
        answer = str(response.content)
        finish_reason = getattr(response, "response_metadata", {}).get("finish_reason")
        info = {
            "finish_reason": finish_reason,
            "usage": getattr(response, "usage_metadata", None),
            "complete": False
            if finish_reason == "length"
            else (True if finish_reason == "stop" else None),
        }
        generation_info.set(info)
        if not answer.strip():
            raise RuntimeError("生成模型未返回有效正文，请检查模型输出限制或上游响应")
        answer, citations = finalize_answer(answer, self.evidence, finish_reason)
        final_step = {
            "id": "answer",
            "type": "answer",
            "status": "done",
            "citations": len(citations),
            "finish_reason": finish_reason,
            "complete": info["complete"],
        }
        self.trace.append(final_step)
        emit_trace(final_step)
        emit_detail(
            {
                "id": "final-context",
                "type": "final_context",
                "evidence_count": len(self.evidence),
                "evidence_ids": [item["id"] for item in self.evidence],
                "citation_ids": [item["id"] for item in citations],
                "finish_reason": finish_reason,
            }
        )
        reasoning_state.set(None)
        return answer, citations, self.tool_log

    def run(self):
        response = (
            self._run_with_tools() if self.search_tool else self._invoke(self.client)
        )
        return self._finalize(response)


def generate(
    question,
    history,
    evidence,
    rag=True,
    search_tool=None,
    max_search_calls=None,
    trace=None,
    versions=None,
):
    return GenerationSession(
        question,
        history,
        evidence,
        rag=rag,
        search_tool=search_tool,
        max_search_calls=max_search_calls,
        trace=trace,
        versions=versions,
    ).run()
