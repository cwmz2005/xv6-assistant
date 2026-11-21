"""Conversation session and message endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..core.database import DB, Message, Session
from ..core.session_lock import session_guard

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def sessions():
    with DB() as db:
        return [
            {"id": session.id, "title": session.title}
            for session in db.scalars(
                select(Session).order_by(Session.updated_at.desc(), Session.id)
            )
        ]


@router.post("")
def create_session():
    with DB() as db:
        session = Session()
        db.add(session)
        db.commit()
        return {"id": session.id}


@router.get("/{sid}/messages")
def messages(sid: str):
    with DB() as db:
        return [
            {
                "role": message.role,
                "content": message.content,
                "citations": message.citations,
                "trace": message.trace or [],
                "details": message.details or [],
            }
            for message in db.scalars(
                select(Message)
                .where(Message.session_id == sid)
                .order_by(Message.sequence)
            )
        ]


@router.delete("/{sid}")
def remove(sid: str):
    with session_guard(sid):
        with DB() as db:
            session = db.get(Session, sid)
            if not session:
                raise HTTPException(404)
            db.delete(session)
            db.commit()
            return {"deleted": sid}
