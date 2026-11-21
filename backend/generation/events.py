"""Runtime sinks for streaming tokens, process traces and generation details."""

from contextlib import contextmanager
from contextvars import ContextVar

token_sink = ContextVar("token_sink", default=None)
generation_info = ContextVar("generation_info", default=None)
trace_sink = ContextVar("trace_sink", default=None)
detail_sink = ContextVar("detail_sink", default=None)
detail_log = ContextVar("detail_log", default=None)
reasoning_state = ContextVar("reasoning_state", default=None)


def emit_trace(step):
    sink = trace_sink.get()
    if sink:
        sink(step)


def emit_detail(event):
    log = detail_log.get()
    if log is not None:
        log.append(event)
    sink = detail_sink.get()
    if sink:
        sink(event)


@contextmanager
def collect_details():
    log = []
    token = detail_log.set(log)
    try:
        yield log
    finally:
        detail_log.reset(token)


class StreamState:
    """Collect provider reasoning for one LLM call and stream it as trace deltas."""

    def __init__(self):
        self.step_id = None
        self.parts = []

    def begin(self, step_id):
        self.step_id = step_id
        self.parts = []

    @property
    def text(self):
        return "".join(self.parts)

    def add(self, text):
        if not text:
            return
        self.parts.append(text)
        if self.step_id:
            emit_trace(
                {
                    "id": self.step_id,
                    "type": "thinking",
                    "status": "delta",
                    "text": text,
                }
            )
