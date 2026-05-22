"""Migrate session times to datetime

Revision ID: 4ba8df5ae9fc
Revises: 6d1d50627bec
Create Date: 2026-05-22 02:18:23.725955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ba8df5ae9fc'
down_revision = '6d1d50627bec'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add columns as nullable=True
    with op.batch_alter_table('break_entry', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_datetime', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('end_datetime', sa.DateTime(), nullable=True))

    with op.batch_alter_table('study_session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_datetime', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('end_datetime', sa.DateTime(), nullable=True))

    # 2. Migrate data — use dialect-appropriate SQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("""
            UPDATE break_entry
            SET start_datetime = "date" + time_in,
                end_datetime = CASE
                    WHEN time_out < time_in THEN ("date" + time_out) + interval '1 day'
                    ELSE "date" + time_out
                END
        """)
        op.execute("""
            UPDATE study_session
            SET start_datetime = "date" + time_in,
                end_datetime = CASE
                    WHEN time_out < time_in THEN ("date" + time_out) + interval '1 day'
                    ELSE "date" + time_out
                END
        """)
    else:
        # SQLite
        op.execute("""
            UPDATE break_entry
            SET start_datetime = date || ' ' || time_in,
                end_datetime = CASE
                    WHEN time_out < time_in THEN datetime(date || ' ' || time_out, '+1 day')
                    ELSE date || ' ' || time_out
                END
        """)
        op.execute("""
            UPDATE study_session
            SET start_datetime = date || ' ' || time_in,
                end_datetime = CASE
                    WHEN time_out < time_in THEN datetime(date || ' ' || time_out, '+1 day')
                    ELSE date || ' ' || time_out
                END
        """)

    # 3. Alter columns to nullable=False and drop old ones
    with op.batch_alter_table('break_entry', schema=None) as batch_op:
        batch_op.alter_column('start_datetime', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('end_datetime', existing_type=sa.DateTime(), nullable=False)
        batch_op.drop_column('time_in')
        batch_op.drop_column('time_out')
        batch_op.drop_column('date')

    with op.batch_alter_table('study_session', schema=None) as batch_op:
        batch_op.alter_column('start_datetime', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('end_datetime', existing_type=sa.DateTime(), nullable=False)
        batch_op.drop_column('time_in')
        batch_op.drop_column('time_out')
        batch_op.drop_column('date')


def downgrade():
    with op.batch_alter_table('study_session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date', sa.DATE(), nullable=False))
        batch_op.add_column(sa.Column('time_out', sa.TIME(), nullable=False))
        batch_op.add_column(sa.Column('time_in', sa.TIME(), nullable=False))
        batch_op.drop_column('end_datetime')
        batch_op.drop_column('start_datetime')

    with op.batch_alter_table('break_entry', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date', sa.DATE(), nullable=False))
        batch_op.add_column(sa.Column('time_out', sa.TIME(), nullable=False))
        batch_op.add_column(sa.Column('time_in', sa.TIME(), nullable=False))
        batch_op.drop_column('end_datetime')
        batch_op.drop_column('start_datetime')
