"""Initial application tables; pgvector must already be enabled."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if not connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")
    ):
        raise RuntimeError("Enable vector in the application database before migrating")
    schema = connection.scalar(sa.text("SELECT current_schema()"))
    tables = set(sa.inspect(connection).get_table_names(schema=schema))
    if "documents" not in tables:
        op.create_table(
            "documents",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("version", sa.String(), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(), nullable=False),
            sa.UniqueConstraint("source", "version", "path"),
        )
    if "chunks" not in tables:
        op.create_table(
            "chunks",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "document_id",
                sa.String(),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(384), nullable=False),
            sa.Column("location", JSONB(), nullable=False),
        )
        op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    if "sessions" not in tables:
        op.create_table(
            "sessions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("title", sa.Text(), nullable=False),
        )
    if "messages" not in tables:
        op.create_table(
            "messages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "session_id",
                sa.String(),
                sa.ForeignKey("sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("citations", JSONB(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
        )
        op.create_index("ix_messages_session_id", "messages", ["session_id"])
    if "retrieval_logs" not in tables:
        op.create_table(
            "retrieval_logs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("payload", JSONB(), nullable=False),
        )


def downgrade():
    raise RuntimeError(
        "Destructive downgrade is intentionally disabled; restore a database backup instead"
    )
