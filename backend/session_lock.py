"""Serialize a conversation across workers while retrieval uses its own commits."""
from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy import text
from .database import engine

@contextmanager
def session_guard(session_id):
    with engine.connect() as connection:
        key=connection.scalar(text('SELECT hashtextextended(:session_id, 0)'),{'session_id':session_id})
        acquired=connection.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':key})
        if not acquired: raise HTTPException(409,'该会话正在生成回答，请稍后重试')
        try: yield
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':key})
