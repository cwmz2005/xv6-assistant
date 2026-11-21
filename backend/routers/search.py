"""Retrieval and strategy-comparison endpoints."""

from fastapi import APIRouter

from ..core.database import DB
from ..retrieval import search
from ..schemas import Query

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
def retrieve(q: Query):
    with DB() as db:
        return search(db, **q.model_dump())


@router.post("/search/compare")
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
