"""Initial schema - baseline migration

This migration establishes the baseline schema state as of December 2024.
It does NOT make schema changes - it's just a marker that the database
was at this state when Alembic was adopted.

The actual table creation is handled by SQLAlchemy's create_all() and
the legacy inline migrations in main.py.

Future migrations should be proper incremental changes.

Revision ID: 001_initial
Revises:
Create Date: 2024-12-09
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Baseline migration - no changes made.

    This migration serves as a marker that Alembic was initialized
    at this schema state. The actual schema is managed by:
    1. SQLAlchemy's create_all() for new deployments
    2. Legacy inline migrations in main.py for existing deployments

    Future migrations should build incrementally from this baseline.
    """
    # Intentionally empty - baseline migration
    # The schema already exists from create_all() and legacy migrations
    pass


def downgrade() -> None:
    """
    Baseline migration - no changes to reverse.
    """
    # Intentionally empty - baseline migration
    pass
