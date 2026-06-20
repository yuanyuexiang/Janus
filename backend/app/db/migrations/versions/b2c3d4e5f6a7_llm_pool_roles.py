"""llm model pool + role assignments

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 旧的按角色单表 → 拆成 模型池 + 角色分配
    op.drop_table('llm_settings')

    op.create_table(
        'llm_models',
        sa.Column('name', sa.String(length=64), primary_key=True),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('api_base', sa.String(length=256), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'llm_role_assignments',
        sa.Column('role', sa.String(length=16), primary_key=True),
        sa.Column('model_name', sa.String(length=64), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('llm_role_assignments')
    op.drop_table('llm_models')
    op.create_table(
        'llm_settings',
        sa.Column('role', sa.String(length=16), primary_key=True),
        sa.Column('model', sa.String(length=128), nullable=True),
        sa.Column('api_base', sa.String(length=256), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
