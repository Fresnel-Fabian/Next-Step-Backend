"""add is_active to users, role to invitations

Revision ID: df80d4542dd3
Revises: 417cc85441cf
Create Date: 2026-04-03 18:13:42.510629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df80d4542dd3'
down_revision: Union[str, Sequence[str], None] = '417cc85441cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add is_active to users if not exists
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    if 'is_active' not in user_columns:
        op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Add role to invitations if not exists
    invitation_columns = [col['name'] for col in inspector.get_columns('invitations')]
    if 'role' not in invitation_columns:
        op.add_column('invitations', sa.Column('role', sa.String(), nullable=False, server_default='STUDENT'))

    # Create invitations table if not exists
    if 'invitations' not in inspector.get_table_names():
        op.create_table(
            'invitations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('token', sa.String(), nullable=False, unique=True),
            sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
            sa.Column('role', sa.String(), nullable=False, server_default='STUDENT'),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
        )

    # Add entity_id index if not exists
    indexes = [idx['name'] for idx in inspector.get_indexes('notifications')]
    if 'ix_notifications_entity_id' not in indexes:
        op.create_index(op.f('ix_notifications_entity_id'), 'notifications', ['entity_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_entity_id'), table_name='notifications')
    op.drop_column('invitations', 'role')
    op.drop_column('users', 'is_active')