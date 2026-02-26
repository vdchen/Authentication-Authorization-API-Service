"""add_user_roles_and_soft_delete

Revision ID: 9804a5059475
Revises: a877c2460d54
Create Date: 2026-02-21 23:21:58.824731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9804a5059475'
down_revision: Union[str, Sequence[str], None] = 'a877c2460d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the 'role' enum type in Postgres
    role_enum = sa.Enum('ADMIN', 'USER', name='role')
    role_enum.create(op.get_bind())

    # 2. Add the new columns to the 'users' table
    op.add_column('users', sa.Column('role', role_enum, nullable=False,
                                     server_default='USER'))
    # op.add_column('users',
    #               sa.Column('is_blocked', sa.Boolean(), nullable=False,
    #                         server_default='false'))
    op.add_column('users', sa.Column('block_at', sa.DateTime(timezone=True),
                                     nullable=True))
    op.add_column('users',
                  sa.Column('is_deleted', sa.Boolean(), nullable=False,
                            server_default='false'))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True),
                                     nullable=True))

    # 3. Handle balance nullability (if you changed it from nullable=False to True)
    op.alter_column('users', 'balance', existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # 1. Remove columns
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'is_deleted')
    op.drop_column('users', 'block_at')
    op.drop_column('users', 'is_blocked')
    op.drop_column('users', 'role')

    # 2. Drop the enum type
    sa.Enum(name='role').drop(op.get_bind())

    # 3. Revert balance nullability
    op.alter_column('users', 'balance', existing_type=sa.Integer(),
                    nullable=False)
