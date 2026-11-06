import uuid
from sqlalchemy import create_engine, String, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from .config import settings
class Base(DeclarativeBase): pass
def uid(): return str(uuid.uuid4())
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    source: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    index_profile: Mapped[str] = mapped_column(String, default='legacy', server_default='legacy')
    __table_args__ = (UniqueConstraint("source", "version", "path"),)
class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[str] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(384))
    location: Mapped[dict] = mapped_column(JSONB)
class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(Text, default="新会话")
class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint('session_id','sequence',name='uq_messages_session_sequence'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    sequence: Mapped[int]
class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    payload: Mapped[dict] = mapped_column(JSONB)
engine = create_engine(settings.url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
DB = sessionmaker(engine)
