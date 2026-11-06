"""Run retrieval ablations against a manually annotated JSONL dataset."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from .config import settings
from .database import DB, Chunk
from .evaluation import metrics
from .evaluation_schema import Experiment
from .evaluation_summary import summarize
from .retrieval import search


def run(dataset, output, k=5, candidates=20, warmup=False):
    cases = [
        json.loads(line)
        for line in Path(dataset).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases or any(c.get("annotation_status") != "complete" for c in cases):
        raise ValueError(
            "Every test case must have annotation_status=complete before evaluation"
        )
    checked = Experiment(cases=cases, top_k=k, candidates=candidates)
    cases = [case.model_dump() for case in checked.cases]
    records = []
    if warmup:
        from .ingestion import embedder
        from .retrieval import reranker

        embedder().embed_query("query: xv6")
        reranker().predict([("xv6", "xv6 operating system")])
    with DB() as db:
        for case in cases:
            ids = set(
                db.scalars(select(Chunk.id).where(Chunk.id.in_(case["relevance"])))
            )
            if ids != set(case["relevance"]):
                raise ValueError("Unknown relevance chunk IDs; verify corpus mapping")
        for case in cases:
            for strategy, rerank in [
                ("dense", False),
                ("hybrid", False),
                ("hybrid", True),
            ]:
                found = search(db, case["question"], strategy, k, candidates, rerank)
                records.append(
                    {
                        "case_id": case["id"],
                        "strategy": strategy,
                        "rerank": rerank,
                        "metrics": metrics(
                            [r["id"] for r in found["results"]], case["relevance"], k
                        ),
                        **found,
                    }
                )
    result = {
        "created_at": datetime.now(UTC).isoformat(),
        "k": k,
        "candidates": candidates,
        "embedding_model": settings.embedding_model,
        "reranker_model": settings.reranker_model,
        "scope": "retrieval_only",
        "warmup": warmup,
        "records": records,
        "summary": summarize(records),
        "dataset_hash": hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        "code_version": settings.default_code_version,
    }
    Path(output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("output")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--candidates", type=int, default=20)
    parser.add_argument("--warmup", action="store_true")
    args = parser.parse_args()
    run(args.dataset, args.output, args.k, args.candidates, args.warmup)
