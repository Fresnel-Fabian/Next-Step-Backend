"""add announcements and notification fields

Revision ID: 417cc85441cf
Revises: 92270b4407e0
Create Date: 2026-03-02 18:19:18.102325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '417cc85441cf'
down_revision: Union[str, Sequence[str], None] = '92270b4407e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('notifications')]

    if 'entity_type' not in existing_columns:
        op.add_column('notifications', sa.Column('entity_type', sa.String(length=50), nullable=True))
    if 'file_url' not in existing_columns:
        op.add_column('notifications', sa.Column('file_url', sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'file_url')
    op.drop_column('notifications', 'entity_type')