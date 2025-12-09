"""Add user authentication tables and fields

Revision ID: 001_add_user_auth
Revises:
Create Date: 2024-12-09

This migration adds:
- users table with authentication fields
- Account lockout fields for brute force protection
- Token versioning for token revocation
- uploaded_by foreign key on media table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_add_user_auth'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table and add auth-related columns."""

    # Create users table if it doesn't exist
    # Using op.execute with IF NOT EXISTS for PostgreSQL compatibility
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('username', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
            sa.Column('hashed_password', sa.String(255), nullable=False),
            sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_login', sa.DateTime(), nullable=True),

            # Extended profile fields
            sa.Column('full_name', sa.String(255), nullable=True),
            sa.Column('date_of_birth', sa.DateTime(), nullable=True),
            sa.Column('city', sa.String(100), nullable=True),
            sa.Column('country', sa.String(100), nullable=True),

            # Consent and verification
            sa.Column('consent_given', sa.Boolean(), server_default='false'),
            sa.Column('consent_date', sa.DateTime(), nullable=True),
            sa.Column('email_verified', sa.Boolean(), server_default='false'),
            sa.Column('email_verification_token', sa.String(255), nullable=True),
            sa.Column('email_verification_sent_at', sa.DateTime(), nullable=True),

            # Account lockout fields
            sa.Column('failed_login_attempts', sa.Integer(), server_default='0'),
            sa.Column('locked_until', sa.DateTime(), nullable=True),
            sa.Column('last_failed_login', sa.DateTime(), nullable=True),

            # Token versioning for revocation
            sa.Column('token_version', sa.Integer(), server_default='0'),
        )
    else:
        # Table exists, add any missing columns
        existing_columns = [col['name'] for col in inspector.get_columns('users')]

        # Add columns that might be missing from older versions
        columns_to_add = [
            ('full_name', sa.String(255)),
            ('date_of_birth', sa.DateTime()),
            ('city', sa.String(100)),
            ('country', sa.String(100)),
            ('consent_given', sa.Boolean()),
            ('consent_date', sa.DateTime()),
            ('email_verified', sa.Boolean()),
            ('email_verification_token', sa.String(255)),
            ('email_verification_sent_at', sa.DateTime()),
            ('failed_login_attempts', sa.Integer()),
            ('locked_until', sa.DateTime()),
            ('last_failed_login', sa.DateTime()),
            ('token_version', sa.Integer()),
        ]

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                op.add_column('users', sa.Column(col_name, col_type, nullable=True))

    # Add uploaded_by to media table if it doesn't exist
    if 'media' in existing_tables:
        media_columns = [col['name'] for col in inspector.get_columns('media')]
        if 'uploaded_by' not in media_columns:
            op.add_column('media', sa.Column('uploaded_by', sa.Integer(), nullable=True))
            op.create_foreign_key(
                'fk_media_uploaded_by_users',
                'media', 'users',
                ['uploaded_by'], ['id']
            )


def downgrade() -> None:
    """Remove users table and auth-related columns."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Remove foreign key and column from media
    if 'media' in existing_tables:
        media_columns = [col['name'] for col in inspector.get_columns('media')]
        if 'uploaded_by' in media_columns:
            try:
                op.drop_constraint('fk_media_uploaded_by_users', 'media', type_='foreignkey')
            except Exception:
                pass  # Constraint might not exist
            op.drop_column('media', 'uploaded_by')

    # Drop users table
    if 'users' in existing_tables:
        op.drop_table('users')
