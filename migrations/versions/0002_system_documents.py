"""Protect the supplied official knowledge sources."""
from pathlib import Path
from alembic import op
from sqlalchemy import text
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    connection=op.get_bind()
    connection.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT false'))
    root=Path(__file__).resolve().parents[2]
    for directory in ['data/labs','data/xv6-labs-2022-impl']:
        connection.execute(text('UPDATE documents SET is_system=true WHERE source=:source'),{'source':str((root/directory).resolve())})

def downgrade():
    raise RuntimeError('System document protection cannot be removed by downgrade')
