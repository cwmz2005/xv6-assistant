"""Initial application tables; pgvector must already be enabled."""
from alembic import op
from sqlalchemy import text
from backend.database import Base

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    if not connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")):
        raise RuntimeError('Enable vector in the application database before migrating')
    Base.metadata.create_all(connection)

def downgrade():
    raise RuntimeError('Destructive downgrade is intentionally disabled; restore a database backup instead')
