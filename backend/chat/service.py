"""Chat orchestration: session context, retrieval, generation and persistence."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from ..core.config import settings
from ..core.database import DB, Message, Session
from ..core.versions import version_options
from ..generation import (
    collect_details,
    emit_detail,
    emit_trace,
    generate,
    generation_info,
)
from ..retrieval import search
from ..schemas import Chat
from .conversation import retrieval_query


@dataclass
class InitialContext:
    effective_query: str
    found: dict
    evidence: list
    trace: list
    candidates: int


def _require_llm():
    if not settings.llm_api_key or not settings.llm_model:
        raise HTTPException(503, "请配置 LLM_API_KEY 和 LLM_MODEL")


def _load_session(db, session_id):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    session.updated_at = datetime.now(UTC)
    return session


def _load_history(db, session_id):
    return list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.sequence)
        )
    )


def _retrieve_initial(db, q: Chat, history):
    effective_query = retrieval_query(q.query, history)
    candidates = q.candidates
    found = (
        search(
            db,
            **{
                **q.model_dump(
                    exclude={
                        "session_id",
                        "rag",
                        "tools",
                        "tool_call_limit",
                    }
                ),
                "query": effective_query,
                "candidates": candidates,
            },
        )
        if q.rag
        else {"results": []}
    )
    evidence = found["results"]
    trace = []
    if q.rag:
        _record_initial_retrieval(
            q, effective_query, found, evidence, candidates, trace
        )
    return InitialContext(effective_query, found, evidence, trace, candidates)


def _record_initial_retrieval(q, effective_query, found, evidence, candidates, trace):
    step = {
        "id": "retrieval-initial",
        "type": "retrieval",
        "status": "done",
        "query": effective_query,
        "count": len(evidence),
        "candidates": candidates,
        "strategy": q.strategy,
        "rerank": q.rerank,
        "retrieval_ms": found.get("retrieval_ms"),
        "reranker_ms": found.get("reranker_ms"),
    }
    trace.append(step)
    emit_trace(step)
    emit_detail(
        {
            "id": "rag-context",
            "type": "rag_context",
            "query": effective_query,
            "strategy": q.strategy,
            "top_k": q.top_k,
            "candidates": candidates,
            "rerank": q.rerank,
            "rrf_k": q.rrf_k,
            "version": q.version,
            "retrieval_ms": found.get("retrieval_ms"),
            "reranker_ms": found.get("reranker_ms"),
            "results": list(evidence),
            "candidate_scores": found.get("candidate_scores", []),
        }
    )


def _make_tool_search(db, q: Chat):
    def tool_search(query, path_regex=None, version=None):
        try:
            return search(
                db,
                query,
                q.strategy,
                q.top_k,
                q.candidates,
                q.rerank,
                q.rrf_k,
                version if version is not None else q.version,
                path_regex=path_regex,
            )
        except Exception as exc:
            return {
                "results": [],
                "candidate_scores": [],
                "retrieval_ms": 0,
                "reranker_ms": 0,
                "error": str(exc),
            }

    return tool_search


def _persist_turn(db, q: Chat, session, history, answer, citations, trace, details):
    if not history:
        session.title = q.query[:80]
    db.add_all(
        [
            Message(
                session_id=q.session_id,
                role="user",
                content=q.query,
                sequence=len(history),
            ),
            Message(
                session_id=q.session_id,
                role="assistant",
                content=answer,
                citations=citations,
                trace=trace,
                details=details,
                sequence=len(history) + 1,
            ),
        ]
    )
    db.commit()


def _response(initial, answer, citations, tool_log, details, started):
    return {
        "answer": answer,
        "citations": citations,
        "trace": initial.trace,
        "details": details,
        "generation": generation_info.get(),
        "retrieval": initial.found,
        "tool_calls": tool_log,
        "end_to_end_ms": (time.perf_counter() - started) * 1000,
    }


def chat_impl(q: Chat):
    _require_llm()
    started = time.perf_counter()
    with collect_details() as details:
        with DB() as db:
            session = _load_session(db, q.session_id)
            history = _load_history(db, q.session_id)
            initial = _retrieve_initial(db, q, history)
            versions = version_options(db) if q.tools and q.rag else []
            tool_search = _make_tool_search(db, q) if q.tools and q.rag else None
            answer, citations, tool_log = generate(
                q.query,
                history,
                initial.evidence,
                q.rag,
                tool_search,
                max_search_calls=q.tool_call_limit,
                trace=initial.trace,
                versions=versions,
            )
            _persist_turn(
                db,
                q,
                session,
                history,
                answer,
                citations,
                initial.trace,
                details,
            )
            return _response(
                initial,
                answer,
                citations,
                tool_log,
                details,
                started,
            )
