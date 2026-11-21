"""Chat endpoints, including the SSE streaming adapter."""

import json
import queue
import threading

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..chat.service import chat_impl
from ..core.session_lock import session_guard
from ..generation import detail_sink, token_sink, trace_sink
from ..schemas import Chat

router = APIRouter(prefix="/api", tags=["chat"])


def _run_locked(q: Chat):
    with session_guard(q.session_id):
        return chat_impl(q)


@router.post("/chat")
def chat_endpoint(q: Chat):
    return _run_locked(q)


@router.post("/chat/stream")
def stream_chat(q: Chat):
    events = queue.Queue()

    def worker():
        token_context = token_sink.set(
            lambda token: events.put(("token", {"text": token}))
        )
        trace_context = trace_sink.set(lambda step: events.put(("trace", step)))
        detail_context = detail_sink.set(lambda event: events.put(("detail", event)))
        try:
            events.put(("done", _run_locked(q)))
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
