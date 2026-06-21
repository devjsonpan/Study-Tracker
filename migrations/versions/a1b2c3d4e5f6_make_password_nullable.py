"""make password column nullable for Google OAuth users

Revision ID: a1b2c3d4e5f6
Revises: 6c926949b88b
Create Date: 2026-06-21 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '6c926949b88b'
branch_labels = None
depends_on = None


def upgrade():
    # Google OAuth users have no password — make column nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password',
                              existing_type=sa.String(),
                              nullable=True)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password',
                              existing_type=sa.String(),
                              nullable=False)
