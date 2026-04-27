"""add access_level to documents

Revision ID: 1569c467b082
Revises: df80d4542dd3
Create Date: 2026-04-25 17:26:25.525925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1569c467b082'
down_revision: Union[str, Sequence[str], None] = 'df80d4542dd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column was already added manually via ALTER TABLE.
    # This migration ensures fresh installs get it too.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('documents')]
    if 'access_level' not in columns:
        op.add_column('documents', sa.Column(
            'access_level',
            sa.String(20),
            server_default='ALL',
            nullable=False,
        ))


def downgrade() -> None:
    op.drop_column('documents', 'access_level')