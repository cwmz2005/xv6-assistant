from alembic import op
from sqlalchemy import text
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
    op.get_bind().execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS index_profile VARCHAR NOT NULL DEFAULT 'legacy'"))
def downgrade():
    raise RuntimeError('Index provenance should not be removed')
