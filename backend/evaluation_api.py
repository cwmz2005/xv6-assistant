"""Explicit human annotations and reproducible retrieval experiments."""

import hashlib
import json
from datetime import UTC, datetime
from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .config import settings
from .database import DB, Chunk, RetrievalLog
from .evaluation import metrics
from .evaluation_schema import Case as Case
from .evaluation_schema import Experiment as Experiment
from .evaluation_summary import summarize
from .retrieval import search

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
    from .jobs import submit

    return submit(
        "evaluation",
        experiment.model_dump(),
        lambda progress: execute(experiment, progress),
    )


@router.post("/run")
def run(experiment: Experiment):
    return execute(experiment)


def execute(experiment: Experiment, progress=None):
    records = []
    if len({case.id for case in experiment.cases}) != len(experiment.cases):
        raise HTTPException(422, "测试集问题 ID 不能重复")
    if experiment.candidates < experiment.top_k:
        raise HTTPException(422, "候选数不能小于 Top K")
    if experiment.generate_answers and not (
        settings.llm_api_key and settings.llm_model
    ):
        raise HTTPException(503, "生成评估需要 LLM 配置")
    with DB() as db:
        for case in experiment.cases:
            if case.annotation_status != "complete" or any(
                g < 0 or g > 3 for g in case.relevance.values()
            ):
                raise HTTPException(422, "请完成人工标注；相关等级必须在 0 到 3 之间")
            if case.type != "out_of_scope" and not any(
                grade > 0 for grade in case.relevance.values()
            ):
                raise HTTPException(422, "库内问题至少需要一个相关片段标注")
            existing = set(
                db.scalars(select(Chunk.id).where(Chunk.id.in_(case.relevance)))
            )
            if existing != set(case.relevance):
                raise HTTPException(422, "标注引用了不存在的片段")
        variants = [("dense", False), ("hybrid", False)]
        if experiment.include_reranker:
            variants.append(("hybrid", True))
        for case in experiment.cases:
            if experiment.generate_answers:
                if progress:
                    progress(
                        {
                            "case_id": case.id,
                            "variant": "baseline",
                            "completed_answers": len(records),
                        }
                    )
                from .generation import generate, generation_info

                start = perf_counter()
                answer, _, _ = generate(case.question, [], [], False)
                records.append(
                    {
                        "case_id": case.id,
                        "strategy": "baseline",
                        "answer": answer,
                        "generation": generation_info.get(),
                        "reference_answer": case.reference_answer,
                        "end_to_end_ms": (perf_counter() - start) * 1000,
                        "accuracy": None,
                        "accuracy_method": "pending human review",
                    }
                )
            for strategy, rerank in variants:
                if progress:
                    progress(
                        {
                            "case_id": case.id,
                            "variant": strategy + ("_rerank" if rerank else ""),
                            "completed_answers": len(records),
                        }
                    )
                start = perf_counter()
                found = search(
                    db,
                    case.question,
                    strategy,
                    experiment.top_k,
                    experiment.candidates,
                    rerank,
                )
                record = {
                    "case_id": case.id,
                    "question_type": case.type,
                    "strategy": strategy,
                    "rerank": rerank,
                    "metrics": metrics(
                        [r["id"] for r in found["results"]],
                        case.relevance,
                        experiment.top_k,
                    ),
                    **found,
                }
                if experiment.generate_answers:
                    answer, citations, _ = generate(case.question, [], found["results"])
                    record.update(
                        answer=answer,
                        citations=citations,
                        reference_answer=case.reference_answer,
                        generation=generation_info.get(),
                        accuracy=None,
                        accuracy_method="pending human review",
                        end_to_end_ms=(perf_counter() - start) * 1000,
                    )
                records.append(record)
        result = {
            "created_at": datetime.now(UTC).isoformat(),
            "scope": "retrieval_and_generation"
            if experiment.generate_answers
            else "retrieval_only",
            "llm_model": settings.llm_model,
            "temperature": 0,
            "max_tokens": settings.llm_max_tokens,
            "reasoning_effort": settings.llm_reasoning_effort,
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
            "parameters": experiment.model_dump(),
            "records": records,
            "accuracy": None,
            "code_version": settings.default_code_version,
            "prompt_version": "concise-v2",
            "dataset_hash": hashlib.sha256(
                json.dumps(
                    [c.model_dump() for c in experiment.cases],
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode()
            ).hexdigest(),
            "summary": summarize(records),
            "limitations": "答案准确性须独立人工核验。无相关证据样本不计算 Recall 和 nDCG。延迟包含按需模型加载，正式实验应先预热并重复测量。",
        }
        log = RetrievalLog(payload={"kind": "experiment", "result": result})
        db.add(log)
        db.commit()
        return {"id": log.id, **result}


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
    from .jobs import submit

    return submit(
        "llm_judge",
        {"experiment_id": experiment_id},
        lambda progress: judge_records(experiment_id, progress),
    )


def judge_records(experiment_id, progress=None):
    from .judge import judge

    with DB() as db:
        log = db.get(RetrievalLog, experiment_id)
        if not log or log.payload.get("kind") != "experiment":
            raise HTTPException(404, "实验不存在")
        payload = json.loads(json.dumps(log.payload))
    result = payload["result"]
    cases = {c["id"]: c for c in result["parameters"]["cases"]}
    for index, record in enumerate(result["records"]):
        if "answer" not in record:
            continue
        if record.get("llm_judge", {}).get("model") == (
            settings.judge_model or settings.llm_model
        ):
            continue
        if progress:
            progress(
                {
                    "case_id": record["case_id"],
                    "completed_answers": index,
                    "variant": record["strategy"],
                }
            )
        case = cases[record["case_id"]]
        record["llm_judge"] = judge(
            case["question"],
            case["reference_answer"],
            record["answer"],
            case.get("answer_criteria"),
        )
        with DB() as checkpoint:
            saved = checkpoint.scalar(
                select(RetrievalLog)
                .where(RetrievalLog.id == experiment_id)
                .with_for_update()
            )
            updated = json.loads(json.dumps(saved.payload))
            updated["result"]["records"][index]["llm_judge"] = record["llm_judge"]
            updated["result"]["summary"] = summarize(updated["result"]["records"])
            saved.payload = updated
            checkpoint.commit()
    with DB() as db:
        log = db.scalar(
            select(RetrievalLog)
            .where(RetrievalLog.id == experiment_id)
            .with_for_update()
        )
        current = json.loads(json.dumps(log.payload))
        for target, source in zip(current["result"]["records"], result["records"]):
            if "llm_judge" in source:
                target["llm_judge"] = source["llm_judge"]
        current["result"]["summary"] = summarize(current["result"]["records"])
        log.payload = current
        db.commit()
        return {"id": experiment_id, **current["result"]}


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
