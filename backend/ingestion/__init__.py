"""Document ingestion: chunking, source discovery and embeddings."""

from .chunking import split
from .pipeline import embedder, ingest

__all__ = ["embedder", "ingest", "split"]
