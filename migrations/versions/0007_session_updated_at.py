"""Track the last question time so sessions can be ordered by recency."""

from alembic import op
from sqlalchemy import text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(
        text(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS updated_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        )
    )
    # Historical messages have no timestamps. Preserve a deterministic initial
    # order from physical insertion order; real times are recorded from now on.
    connection.execute(
        text(
            """
            WITH ordered AS (
                SELECT id, row_number() OVER (ORDER BY ctid DESC) AS rn
                FROM sessions
            )
            UPDATE sessions AS s
            SET updated_at = now() - (ordered.rn * interval '1 second')
            FROM ordered
            WHERE s.id = ordered.id
            """
        )
    )


def downgrade():
    raise RuntimeError("Session recency ordering should not be removed")
