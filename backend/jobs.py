"""Persistent single-process work queue for local imports and experiments."""

import os
import platform
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import psutil
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .database import DB, RetrievalLog

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="xv6-jobs")
worker_host = platform.node()
worker_pid = os.getpid()
worker_started = psutil.Process(worker_pid).create_time()


def worker_alive(payload):
    if payload.get("worker_host", worker_host) != worker_host:
        return True
    pid = payload.get("worker_pid")
    if not pid or pid <= 0:
        return False
    try:
        return (
            abs(psutil.Process(pid).create_time() - payload.get("worker_started", 0))
            < 0.01
        )
    except psutil.AccessDenied:
        return True
    except psutil.NoSuchProcess:
        return False


def recover_interrupted():
    with DB() as db:
        for job in db.scalars(
            select(RetrievalLog).where(RetrievalLog.payload["kind"].astext == "job")
        ):
            if job.payload.get("status") in {"queued", "running"} and not worker_alive(
                job.payload
            ):
                job.payload = {
                    **job.payload,
                    "status": "failed",
                    "error": "服务重启导致任务中断，请重新提交。",
                    "updated_at": now(),
                }
        db.commit()


def now():
    return datetime.now(UTC).isoformat()


def update(job_id, **changes):
    with DB() as db:
        job = db.get(RetrievalLog, job_id)
        job.payload = {**job.payload, **changes, "updated_at": now()}
        db.commit()


def submit(kind, parameters, operation):
    with DB() as db:
        job = RetrievalLog(
            payload={
                "kind": "job",
                "job_type": kind,
                "status": "queued",
                "parameters": parameters,
                "created_at": now(),
                "updated_at": now(),
                "worker_host": worker_host,
                "worker_pid": worker_pid,
                "worker_started": worker_started,
            }
        )
        db.add(job)
        db.commit()
        job_id = job.id

    def work():
        try:
            update(job_id, status="running")
            result = operation(lambda progress: update(job_id, progress=progress))
            update(job_id, status="completed", result=result)
        except Exception as error:
            update(
                job_id, status="failed", error=type(error).__name__ + ": " + str(error)
            )

    executor.submit(work)
    return {"id": job_id, "status": "queued"}


@router.get("")
def list_jobs():
    with DB() as db:
        rows = db.scalars(
            select(RetrievalLog).where(RetrievalLog.payload["kind"].astext == "job")
        )
        return sorted(
            [{"id": r.id, **r.payload} for r in rows],
            key=lambda r: r["created_at"],
            reverse=True,
        )[:100]


@router.get("/{job_id}")
def get_job(job_id: str):
    with DB() as db:
        job = db.get(RetrievalLog, job_id)
        if not job or job.payload.get("kind") != "job":
            raise HTTPException(404, "任务不存在")
        return {"id": job.id, **job.payload}
