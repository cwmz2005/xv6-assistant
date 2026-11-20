import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select

from .config import settings
from .database import DB, Chunk, Document, Message, Session
from .evaluation_api import router as evaluation_router
from .ingestion import ingest
from .jobs import router as jobs_router
from .retrieval import search


@asynccontextmanager
async def lifespan(application):
    from .jobs import recover_interrupted

    recover_interrupted()
    yield


app = FastAPI(title="xv6 RAG", lifespan=lifespan)

app.include_router(evaluation_router)

app.include_router(jobs_router)


class Query(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    strategy: str = Field(default="hybrid", pattern="^(dense|bm25|hybrid)$")
    top_k: int = Field(default=5, ge=1, le=30)
    candidates: int = Field(default=20, ge=1, le=100)
    rerank: bool = True
    rrf_k: int = Field(default=60, ge=1)
    version: str | None = None

    @model_validator(mode="after")
    def validate_candidates(self):
        if self.candidates < self.top_k:
            raise ValueError("候选数不能小于 Top K")
        return self


class Chat(Query):
    session_id: str
    rag: bool = True
    tools: bool = False
    tool_call_limit: int | None = Field(default=None, ge=1, le=100)


class Import(BaseModel):
    root: str
    commit: str | None = None


@app.get("/api/versions")
def versions():
    with DB() as db:
        return list(
            db.scalars(
                select(Document.version)
                .distinct()
                .where(~Document.version.like("directory-%"))
            )
        )


@app.get("/api/versions/details")
def version_details():
    import json

    manifest = Path(__file__).resolve().parents[1] / "evaluation/source-versions.json"
    names = (
        {
            row["commit"]: row["branch"]
            for row in json.loads(manifest.read_text(encoding="utf-8"))
        }
        if manifest.exists()
        else {}
    )
    return [
        {"version": version, "label": names.get(version, "自定义源码")}
        for version in versions()
    ]


@app.post("/api/import")
def import_data(q: Import):
    with DB() as db:
        return {"chunks": ingest(db, q.root, q.commit)}


@app.post("/api/import/jobs", status_code=202)
def import_job(q: Import):
    from .jobs import submit

    def operation(progress):
        with DB() as db:
            return {"chunks": ingest(db, q.root, q.commit, progress)}

    return submit("import", q.model_dump(), operation)


@app.post("/api/search")
def retrieve(q: Query):
    with DB() as db:
        return search(db, **q.model_dump())


@app.post("/api/search/compare")
def compare_retrieval(q: Query):
    options = q.model_dump(exclude={"strategy", "rerank"})
    variants = [
        ("bm25", "bm25", False),
        ("dense", "dense", False),
        ("hybrid", "hybrid", False),
    ]
    if q.rerank:
        variants.append(("hybrid_rerank", "hybrid", True))
    with DB() as db:
        return {
            name: search(db, strategy=strategy, rerank=rerank, **options)
            for name, strategy, rerank in variants
        }


@app.get("/api/documents")
def documents():
    with DB() as db:
        rows = db.execute(
            select(Document, func.count(Chunk.id))
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .group_by(Document.id)
        ).all()
        return [
            {
                "id": d.id,
                "path": d.path,
                "commit": d.version,
                "source": d.source,
                "hash": d.content_hash,
                "chunks": count,
                "is_system": d.is_system,
            }
            for d, count in rows
        ]


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    with DB() as db:
        document = db.scalar(
            select(Document).where(Document.id == document_id).with_for_update()
        )
        if not document:
            raise HTTPException(404, "文档不存在")
        if document.is_system:
            raise HTTPException(403, "系统文档受保护，不能删除")
        db.delete(document)
        db.commit()
        return {"deleted": document_id}


@app.get("/api/documents/{document_id}/chunks")
def document_chunks(document_id: str):
    with DB() as db:
        return [
            {"id": c.id, "text": c.text, "location": c.location}
            for c in db.scalars(select(Chunk).where(Chunk.document_id == document_id))
        ]


@app.get("/api/sessions")
def sessions():
    with DB() as db:
        return [{"id": s.id, "title": s.title} for s in db.scalars(select(Session))]


@app.post("/api/sessions")
def create_session():
    with DB() as db:
        s = Session()
        db.add(s)
        db.commit()
        return {"id": s.id}


@app.get("/api/sessions/{sid}/messages")
def messages(sid: str):
    with DB() as db:
        return [
            {
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "trace": m.trace or [],
                "details": m.details or [],
            }
            for m in db.scalars(
                select(Message)
                .where(Message.session_id == sid)
                .order_by(Message.sequence)
            )
        ]


@app.delete("/api/sessions/{sid}")
def remove(sid: str):
    from .session_lock import session_guard

    with session_guard(sid):
        with DB() as db:
            s = db.get(Session, sid)
            if not s:
                raise HTTPException(404)
            db.delete(s)
            db.commit()
            return {"deleted": sid}


@app.post("/api/chat")
def chat(q: Chat):
    from .session_lock import session_guard

    with session_guard(q.session_id):
        return chat_impl(q)


def chat_impl(q: Chat):
    from .generation import collect_details

    with collect_details() as details:
        return _chat_impl(q, details)


def _chat_impl(q: Chat, details):
    if not settings.llm_api_key or not settings.llm_model:
        raise HTTPException(503, "请配置 LLM_API_KEY 和 LLM_MODEL")

    t = time.perf_counter()
    with DB() as db:
        session = db.get(Session, q.session_id)
        if not session:
            raise HTTPException(404, "会话不存在")
        history = list(
            db.scalars(
                select(Message)
                .where(Message.session_id == q.session_id)
                .order_by(Message.sequence)
            )
        )
        from .conversation import retrieval_query

        effective_query = retrieval_query(q.query, history)
        initial_candidates = min(q.candidates, q.top_k)
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
                    "candidates": initial_candidates,
                },
            )
            if q.rag
            else {"results": []}
        )
        evidence = found["results"]
        from .generation import (
            emit_detail,
            emit_trace,
            generate,
            generation_info,
        )

        trace = []
        if q.rag:
            step = {
                "id": "retrieval-initial",
                "type": "retrieval",
                "status": "done",
                "query": effective_query,
                "count": len(evidence),
                "candidates": initial_candidates,
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
                    "candidates": initial_candidates,
                    "rerank": q.rerank,
                    "rrf_k": q.rrf_k,
                    "version": q.version,
                    "retrieval_ms": found.get("retrieval_ms"),
                    "reranker_ms": found.get("reranker_ms"),
                    "results": list(evidence),
                    "candidate_scores": found.get("candidate_scores", []),
                }
            )

        def tool_search(query, path_regex=None):
            try:
                return search(
                    db,
                    query,
                    q.strategy,
                    q.top_k,
                    q.candidates,
                    q.rerank,
                    q.rrf_k,
                    q.version,
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

        answer, citations, tool_log = generate(
            q.query,
            history,
            evidence,
            q.rag,
            tool_search if q.tools and q.rag else None,
            max_search_calls=q.tool_call_limit,
            trace=trace,
        )
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
        return {
            "answer": answer,
            "citations": citations,
            "trace": trace,
            "details": details,
            "generation": generation_info.get(),
            "retrieval": found,
            "tool_calls": tool_log,
            "end_to_end_ms": (time.perf_counter() - t) * 1000,
        }


@app.post("/api/chat/stream")
def stream_chat(q: Chat):
    import json
    import queue
    import threading

    from fastapi.responses import StreamingResponse

    from .generation import detail_sink, token_sink, trace_sink

    events = queue.Queue()

    def worker():
        token_context = token_sink.set(
            lambda token: events.put(("token", {"text": token}))
        )
        trace_context = trace_sink.set(lambda step: events.put(("trace", step)))
        detail_context = detail_sink.set(lambda event: events.put(("detail", event)))
        try:
            events.put(("done", chat(q)))
        except Exception as exc:
            events.put(("error", {"message": str(exc)}))
        finally:
            detail_sink.reset(detail_context)
            trace_sink.reset(trace_context)
            token_sink.reset(token_context)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            try:
                kind, payload = events.get(timeout=15)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            yield f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if kind in {"done", "error"}:
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
