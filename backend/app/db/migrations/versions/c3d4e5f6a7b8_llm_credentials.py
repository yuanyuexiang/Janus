"""llm credentials + per-role (credential, model) assignments

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-20 02:00:00.000000

模型池(单模型) → 厂商凭据(名称+厂商+key+缓存模型列表)；角色分配改为 (凭据, 模型)。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('llm_role_assignments')
    op.drop_table('llm_models')

    op.create_table(
        'llm_credentials',
        sa.Column('name', sa.String(length=64), primary_key=True),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('api_base', sa.String(length=256), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column('models', postgresql.JSONB(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'llm_role_assignments',
        sa.Column('role', sa.String(length=24), primary_key=True),
        sa.Column('credential_name', sa.String(length=64), nullable=True),
        sa.Column('model', sa.String(length=128), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('llm_role_assignments')
    op.drop_table('llm_credentials')

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
