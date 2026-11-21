"""Version, import and document-catalog endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..core.database import DB, Chunk, Document
from ..core.jobs import submit
from ..ingestion import ingest
from ..schemas import Import

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/versions")
def versions():
    with DB() as db:
        return list(
            db.scalars(
                select(Document.version)
                .distinct()
                .where(~Document.version.like("directory-%"))
            )
        )


@router.get("/versions/details")
def version_details():
    manifest = Path(__file__).resolve().parents[2] / "evaluation/source-versions.json"
    names = (
        {
            row["commit"]: row["branch"]
            for row in json.loads(manifest.read_text(encoding="utf-8"))
        }
        if manifest.exists()
        else {}
    )
    return [
        {"version": version, "label": names.get(version, "自定义源码")}
        for version in versions()
    ]


@router.post("/import")
def import_data(q: Import):
    with DB() as db:
        return {"chunks": ingest(db, q.root, q.commit)}


@router.post("/import/jobs", status_code=202)
def import_job(q: Import):
    def operation(progress):
        with DB() as db:
            return {"chunks": ingest(db, q.root, q.commit, progress)}

    return submit("import", q.model_dump(), operation)


@router.get("/documents")
def documents():
    with DB() as db:
        rows = db.execute(
            select(Document, func.count(Chunk.id))
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .group_by(Document.id)
        ).all()
        return [
            {
                "id": document.id,
                "path": document.path,
                "commit": document.version,
                "source": document.source,
                "hash": document.content_hash,
                "chunks": count,
                "is_system": document.is_system,
            }
            for document, count in rows
        ]


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    with DB() as db:
        document = db.scalar(
            select(Document).where(Document.id == document_id).with_for_update()
        )
        if not document:
            raise HTTPException(404, "文档不存在")
        if document.is_system:
            raise HTTPException(403, "系统文档受保护，不能删除")
        db.delete(document)
        db.commit()
        return {"deleted": document_id}


@router.get("/documents/{document_id}/chunks")
def document_chunks(document_id: str):
    with DB() as db:
        return [
            {"id": chunk.id, "text": chunk.text, "location": chunk.location}
            for chunk in db.scalars(
                select(Chunk).where(Chunk.document_id == document_id)
            )
        ]
