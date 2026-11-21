"""Retrieval experiment execution and model-assisted judging."""

import hashlib
import json
from datetime import UTC, datetime
from time import perf_counter

from fastapi import HTTPException
from sqlalchemy import select

from ..core.config import settings
from ..core.database import DB, Chunk, RetrievalLog
from ..retrieval import search
from .metrics import metrics
from .schemas import Experiment
from .summary import summarize


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
        _validate_cases(db, experiment)
        variants = [("dense", False), ("hybrid", False)]
        if experiment.include_reranker:
            variants.append(("hybrid", True))
        for case in experiment.cases:
            if experiment.generate_answers:
                _baseline_record(case, records, progress)
            for strategy, rerank in variants:
                _retrieval_record(
                    db, experiment, case, strategy, rerank, records, progress
                )
        result = _build_result(experiment, records)
        log = RetrievalLog(payload={"kind": "experiment", "result": result})
        db.add(log)
        db.commit()
        return {"id": log.id, **result}


def _validate_cases(db, experiment):
    for case in experiment.cases:
        if case.annotation_status != "complete" or any(
            grade < 0 or grade > 3 for grade in case.relevance.values()
        ):
            raise HTTPException(422, "请完成人工标注；相关等级必须在 0 到 3 之间")
        if case.type != "out_of_scope" and not any(
            grade > 0 for grade in case.relevance.values()
        ):
            raise HTTPException(422, "库内问题至少需要一个相关片段标注")
        existing = set(db.scalars(select(Chunk.id).where(Chunk.id.in_(case.relevance))))
        if existing != set(case.relevance):
            raise HTTPException(422, "标注引用了不存在的片段")


def _progress(progress, case_id, variant, records):
    if progress:
        progress(
            {
                "case_id": case_id,
                "variant": variant,
                "completed_answers": len(records),
            }
        )


def _baseline_record(case, records, progress):
    from ..generation import generate, generation_info

    _progress(progress, case.id, "baseline", records)
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


def _retrieval_record(db, experiment, case, strategy, rerank, records, progress):
    from ..generation import generate, generation_info

    _progress(
        progress,
        case.id,
        strategy + ("_rerank" if rerank else ""),
        records,
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
            [result["id"] for result in found["results"]],
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


def _build_result(experiment, records):
    return {
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
                [case.model_dump() for case in experiment.cases],
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest(),
        "summary": summarize(records),
        "limitations": "答案准确性须独立人工核验。无相关证据样本不计算 Recall 和 nDCG。延迟包含按需模型加载，正式实验应先预热并重复测量。",
    }


def judge_records(experiment_id, progress=None):
    from .judge import judge

    with DB() as db:
        log = db.get(RetrievalLog, experiment_id)
        if not log or log.payload.get("kind") != "experiment":
            raise HTTPException(404, "实验不存在")
        payload = json.loads(json.dumps(log.payload))
    result = payload["result"]
    cases = {case["id"]: case for case in result["parameters"]["cases"]}
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
        _save_judge_checkpoint(experiment_id, index, record["llm_judge"])
    return _merge_judge_results(experiment_id, result)


def _save_judge_checkpoint(experiment_id, index, judgment):
    with DB() as checkpoint:
        saved = checkpoint.scalar(
            select(RetrievalLog)
            .where(RetrievalLog.id == experiment_id)
            .with_for_update()
        )
        updated = json.loads(json.dumps(saved.payload))
        updated["result"]["records"][index]["llm_judge"] = judgment
        updated["result"]["summary"] = summarize(updated["result"]["records"])
        saved.payload = updated
        checkpoint.commit()


def _merge_judge_results(experiment_id, result):
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
