from alembic import op
from sqlalchemy import text
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None
def upgrade():
    connection=op.get_bind()
    if not connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_messages_session_sequence' AND conrelid='messages'::regclass)")):
        op.create_unique_constraint('uq_messages_session_sequence','messages',['session_id','sequence'])
def downgrade():
    raise RuntimeError('Message ordering integrity should not be removed')
