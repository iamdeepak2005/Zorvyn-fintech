"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    user_role = sa.Enum('ADMIN', 'ANALYST', 'VIEWER', name='user_role')
    record_type = sa.Enum('INCOME', 'EXPENSE', name='record_type')
    user_role.create(op.get_bind(), checkfirst=True)
    record_type.create(op.get_bind(), checkfirst=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'ANALYST', 'VIEWER', name='user_role', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Financial records table
    op.create_table(
        'financial_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('type', sa.Enum('INCOME', 'EXPENSE', name='record_type', create_type=False), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('amount > 0', name='check_amount_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Performance indexes on financial_records
    op.create_index('idx_records_date', 'financial_records', ['date'])
    op.create_index('idx_records_category', 'financial_records', ['category'])
    op.create_index('idx_records_type', 'financial_records', ['type'])
    op.create_index('idx_records_user_id', 'financial_records', ['user_id'])

    # Partial index for active (non-deleted) records — advanced optimization
    op.execute(
        "CREATE INDEX idx_records_not_deleted ON financial_records(id) WHERE deleted_at IS NULL"
    )

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Idempotency keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_idempotency_keys_key', 'idempotency_keys', ['key'], unique=True)


def downgrade() -> None:
    op.drop_table('idempotency_keys')
    op.drop_table('audit_logs')
    op.drop_index('idx_records_not_deleted', table_name='financial_records')
    op.drop_index('idx_records_user_id', table_name='financial_records')
    op.drop_index('idx_records_type', table_name='financial_records')
    op.drop_index('idx_records_category', table_name='financial_records')
    op.drop_index('idx_records_date', table_name='financial_records')
    op.drop_table('financial_records')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    # Drop enums
    sa.Enum(name='record_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
