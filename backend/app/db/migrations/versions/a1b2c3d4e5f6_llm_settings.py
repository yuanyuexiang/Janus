"""llm_settings

Revision ID: a1b2c3d4e5f6
Revises: 917df7461cf1
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '917df7461cf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_settings',
        sa.Column('role', sa.String(length=16), primary_key=True),
        sa.Column('model', sa.String(length=128), nullable=True),
        sa.Column('api_base', sa.String(length=256), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table('llm_settings')
