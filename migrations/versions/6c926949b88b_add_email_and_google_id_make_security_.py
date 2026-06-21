"""add email and google_id, make security fields nullable

Revision ID: 6c926949b88b
Revises: 4ba8df5ae9fc
Create Date: 2026-06-20 23:33:24.103124

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c926949b88b'
down_revision = '4ba8df5ae9fc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('google_id', sa.String(), nullable=True))
        batch_op.drop_column('security_question')
        batch_op.drop_column('security_answer')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_user_email', ['email'])
        batch_op.create_unique_constraint('uq_user_google_id', ['google_id'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_google_id', type_='unique')
        batch_op.drop_constraint('uq_user_email', type_='unique')
        batch_op.drop_column('google_id')
        batch_op.drop_column('email')
        batch_op.add_column(sa.Column('security_answer', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('security_question', sa.VARCHAR(), nullable=True))
