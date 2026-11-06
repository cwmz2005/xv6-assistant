import uuid
from sqlalchemy import create_engine, String, Text, ForeignKey, UniqueConstraint
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
    title: Mapped[str] = mapped_column(Text, default="???")
class Message(Base):
    __tablename__ = "messages"
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
engine = create_engine(settings.url, pool_pre_ping=True)
DB = sessionmaker(engine)
