"""Knowledge-search tool contract, cache and event emission."""

import json
import re
from dataclasses import dataclass

from .events import emit_detail, emit_trace
from .formatting import top_results

SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "knowledge_search",
        "description": (
            "搜索 xv6 知识库补充证据。query 使用 2–5 个精确技术关键词"
            "（函数名、类型名、文件名或常量），不要复述整句问题，"
            "也不要把未证实的猜测写进查询。可选 path_regex 限定片段路径或来源。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "maxLength": 1000},
                "path_regex": {
                    "type": "string",
                    "maxLength": 200,
                    "description": (
                        "可选的 PostgreSQL 正则，匹配片段文件路径或来源"
                        r"（location.path），例如 kernel/.*\.c$ 只查内核源码，"
                        r"book-.*\.pdf 只查教材。不要用它代替关键词 query。"
                    ),
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class ParsedCall:
    query: str
    path_regex: str | None
    regex_error: str | None


def parse_call(call):
    query = str(call["args"].get("query", ""))[:1000].strip()
    path_regex = str(call["args"].get("path_regex") or "")[:200].strip() or None
    regex_error = None
    if path_regex:
        try:
            re.compile(path_regex)
        except re.error as exc:
            regex_error = str(exc)
    return query, path_regex, regex_error


class SearchToolRunner:
    """Executes one round of model-requested searches with caching and events."""

    def __init__(self, search_tool, max_search_calls, evidence, trace):
        self.search_tool = search_tool
        self.max_search_calls = max_search_calls
        self.evidence = evidence
        self.trace = trace
        self.cache = {}
        self.tool_log = []
        self.stagnant_rounds = 0
        self.added_this_round = 0

    def begin_round(self):
        self.added_this_round = 0

    def end_round(self):
        self.stagnant_rounds = (
            self.stagnant_rounds + 1 if self.added_this_round == 0 else 0
        )

    def should_stop(self):
        return self.stagnant_rounds >= 2 or (
            self.max_search_calls is not None
            and len(self.cache) >= self.max_search_calls
        )

    def handle(self, call, round_number, index):
        query, path_regex, regex_error = parse_call(call)
        step_id = f"search-{round_number}-{index + 1}"
        cache_key = (query, path_regex)
        allowed = (
            call["name"] == "knowledge_search"
            and query
            and regex_error is None
            and (
                cache_key in self.cache
                or self.max_search_calls is None
                or len(self.cache) < self.max_search_calls
            )
        )
        if not allowed:
            reason = "查询无效或已达到检索次数上限"
            if regex_error:
                reason = f"path_regex 无效：{regex_error}"
            self._record_skipped(step_id, round_number, query, path_regex, reason)
            return json.dumps({"error": reason}, ensure_ascii=False)

        reused = cache_key in self.cache
        emit_detail(
            {
                "id": step_id,
                "type": "tool_call",
                "round": round_number,
                "query": query,
                "path_regex": path_regex,
                "cached": reused,
            }
        )
        if not reused:
            emit_trace(
                {
                    "id": step_id,
                    "type": "search",
                    "status": "running",
                    "round": round_number,
                    "query": query,
                    "path_regex": path_regex,
                }
            )
            result = (
                self.search_tool(query, path_regex)
                if path_regex
                else self.search_tool(query)
            )
            self.cache[cache_key] = result
            self.tool_log.append({"query": query, "path_regex": path_regex, **result})
        else:
            result = self.cache[cache_key]

        self._emit_result(step_id, round_number, query, path_regex, reused, result)
        if result.get("error"):
            self._record_skipped(
                step_id,
                round_number,
                query,
                path_regex,
                f"检索失败：{result['error']}",
            )
            return json.dumps(
                {"error": f"Search failed: {result['error']}"}, ensure_ascii=False
            )

        existing = {item["id"] for item in self.evidence}
        new = [item for item in result["results"] if item["id"] not in existing]
        self.evidence.extend(new)
        self.added_this_round += len(new)
        step = {
            "id": step_id,
            "type": "search",
            "status": "done",
            "round": round_number,
            "query": query,
            "path_regex": path_regex,
            "cached": reused,
            "added": len(new),
            "total": len(self.evidence),
            "candidates": len(result.get("candidate_scores") or []),
            "retrieval_ms": result.get("retrieval_ms"),
            "reranker_ms": result.get("reranker_ms"),
            "top": top_results(result.get("results") or []),
        }
        self.trace.append(step)
        emit_trace(step)
        return json.dumps({"results": result["results"]}, ensure_ascii=False)

    def _emit_result(self, step_id, round_number, query, path_regex, reused, result):
        emit_detail(
            {
                "id": step_id,
                "type": "tool_result",
                "round": round_number,
                "query": query,
                "path_regex": path_regex,
                "cached": reused,
                "results": result.get("results") or [],
                "candidate_scores": result.get("candidate_scores") or [],
                "retrieval_ms": result.get("retrieval_ms"),
                "reranker_ms": result.get("reranker_ms"),
                "error": result.get("error"),
            }
        )

    def _record_skipped(self, step_id, round_number, query, path_regex, reason):
        step = {
            "id": step_id,
            "type": "search",
            "status": "skipped",
            "round": round_number,
            "query": query,
            "path_regex": path_regex,
            "reason": reason,
        }
        self.trace.append(step)
        emit_trace(step)
