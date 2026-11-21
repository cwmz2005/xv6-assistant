"""HTTP endpoints for explicit human annotations and experiments."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..core.database import DB, RetrievalLog
from .schemas import Experiment
from .service import execute, judge_records
from .summary import summarize

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("")
def list_experiments():
    with DB() as db:
        rows = db.scalars(
            select(RetrievalLog).where(
                RetrievalLog.payload["kind"].astext == "experiment"
            )
        )
        results = []
        for log in rows:
            result = log.payload["result"]
            results.append(
                {
                    "id": log.id,
                    "scope": result["scope"],
                    "cases": len(result["parameters"]["cases"]),
                    "created_at": result.get("created_at", ""),
                    "model": result.get("llm_model", ""),
                }
            )
        return sorted(results, key=lambda item: item["created_at"], reverse=True)[:100]


@router.post("/jobs", status_code=202)
def experiment_job(experiment: Experiment):
    from ..core.jobs import submit

    return submit(
        "evaluation",
        experiment.model_dump(),
        lambda progress: execute(experiment, progress),
    )


@router.post("/run")
def run(experiment: Experiment):
    return execute(experiment)


@router.get("/{experiment_id}")
def export(experiment_id: str):
    with DB() as db:
        log = db.get(RetrievalLog, experiment_id)
        if not log or log.payload.get("kind") != "experiment":
            raise HTTPException(404)
        return log.payload["result"]


class Review(BaseModel):
    record_index: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    reviewer: str = Field(min_length=1, max_length=100)
    notes: str = Field(min_length=1, max_length=4000)


@router.post("/{experiment_id}/judge", status_code=202)
def judge_experiment(experiment_id: str):
    from ..core.jobs import submit

    return submit(
        "llm_judge",
        {"experiment_id": experiment_id},
        lambda progress: judge_records(experiment_id, progress),
    )


@router.post("/{experiment_id}/reviews")
def review(experiment_id: str, annotation: Review):
    with DB() as db:
        log = db.scalar(
            select(RetrievalLog)
            .where(RetrievalLog.id == experiment_id)
            .with_for_update()
        )
        if not log or log.payload.get("kind") != "experiment":
            raise HTTPException(404)
        payload = json.loads(json.dumps(log.payload))
        result = payload["result"]
        if annotation.record_index >= len(result["records"]):
            raise HTTPException(422, "记录索引超出范围")
        record = result["records"][annotation.record_index]
        if "answer" not in record:
            raise HTTPException(422, "仅可评分已生成的回答")
        record["human_review"] = annotation.model_dump(exclude={"record_index"})
        record["accuracy"] = annotation.score
        record["accuracy_method"] = "human review"
        result["summary"] = summarize(result["records"])
        log.payload = payload
        db.commit()
        return result
