"""Add dual crop fields to officer_appearances

Revision ID: 002_add_dual_crops
Revises: 001_add_user_auth
Create Date: 2024-12-12

This migration adds:
- face_crop_path: Close-up face crop for Officer Card display
- body_crop_path: Full body crop (head to toe) for evidence documentation

These fields support the enhanced officer detection pipeline that generates
two types of crops per officer for better identification and documentation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_dual_crops'
down_revision: Union[str, None] = '001_add_user_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add face_crop_path and body_crop_path columns to officer_appearances."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'officer_appearances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officer_appearances')]

        # Add face_crop_path if not exists
        if 'face_crop_path' not in existing_columns:
            op.add_column(
                'officer_appearances',
                sa.Column('face_crop_path', sa.String(), nullable=True)
            )

        # Add body_crop_path if not exists
        if 'body_crop_path' not in existing_columns:
            op.add_column(
                'officer_appearances',
                sa.Column('body_crop_path', sa.String(), nullable=True)
            )

        # Keep image_crop_path for backwards compatibility (legacy field)
        # It will continue to store the primary crop path

        # Data migration: populate new fields from existing image_crop_path
        # For existing records, use image_crop_path as face_crop_path
        # (since original crops were face-focused)
        if 'image_crop_path' in existing_columns:
            conn.execute(
                sa.text("""
                    UPDATE officer_appearances
                    SET face_crop_path = image_crop_path
                    WHERE face_crop_path IS NULL
                    AND image_crop_path IS NOT NULL
                """)
            )


def downgrade() -> None:
    """Remove face_crop_path and body_crop_path columns."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'officer_appearances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officer_appearances')]

        if 'face_crop_path' in existing_columns:
            op.drop_column('officer_appearances', 'face_crop_path')

        if 'body_crop_path' in existing_columns:
            op.drop_column('officer_appearances', 'body_crop_path')
