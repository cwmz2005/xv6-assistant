"""Persist complete generation details, including prompts and RAG evidence."""

from alembic import op
from sqlalchemy import text

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(
        text(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )


def downgrade():
    raise RuntimeError("Generation detail history should not be removed")
