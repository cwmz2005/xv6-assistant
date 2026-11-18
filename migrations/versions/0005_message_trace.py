"""Persist the assistant's observable thinking and search process."""

from alembic import op
from sqlalchemy import text

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(
        text(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS trace JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )


def downgrade():
    raise RuntimeError("Conversation process history should not be removed")
