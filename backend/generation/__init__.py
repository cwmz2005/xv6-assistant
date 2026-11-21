"""Evidence-bound generation and optional knowledge-base search."""

from . import client
from .client import model
from .core import generate
from .events import (
    StreamState,
    collect_details,
    detail_sink,
    emit_detail,
    emit_trace,
    generation_info,
    reasoning_state,
    token_sink,
    trace_sink,
)

__all__ = [
    "StreamState",
    "client",
    "collect_details",
    "detail_sink",
    "emit_detail",
    "emit_trace",
    "generate",
    "generation_info",
    "model",
    "reasoning_state",
    "token_sink",
    "trace_sink",
]
