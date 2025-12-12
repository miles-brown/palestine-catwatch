"""Add provenance tracking fields to media table

Revision ID: 003_add_provenance
Revises: 002_add_dual_crops
Create Date: 2024-12-12

This migration adds source attribution fields to track where scraped media
originated from, including:
- source_url: Original article URL
- source_name: Publisher name (BBC News, The Guardian, etc.)
- caption: Photo caption from the article
- rights_holder: Copyright holder (PA Images, Reuters, etc.)
- photographer: Individual photographer credit
- article_headline: Article title for context
- article_summary: Brief summary of the article
- scraped_at: Timestamp when the media was scraped

These fields enable proper attribution and provenance tracking for media
scraped from news sources.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_provenance'
down_revision: Union[str, None] = '002_add_dual_crops'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add provenance tracking columns to media table."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'media' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('media')]

        # Add source_url if not exists
        if 'source_url' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('source_url', sa.String(), nullable=True)
            )
            op.create_index('ix_media_source_url', 'media', ['source_url'])

        # Add source_name if not exists
        if 'source_name' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('source_name', sa.String(100), nullable=True)
            )
            op.create_index('ix_media_source_name', 'media', ['source_name'])

        # Add caption if not exists
        if 'caption' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('caption', sa.Text(), nullable=True)
            )

        # Add rights_holder if not exists
        if 'rights_holder' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('rights_holder', sa.String(200), nullable=True)
            )

        # Add photographer if not exists
        if 'photographer' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('photographer', sa.String(200), nullable=True)
            )

        # Add article_headline if not exists
        if 'article_headline' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('article_headline', sa.String(500), nullable=True)
            )

        # Add article_summary if not exists
        if 'article_summary' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('article_summary', sa.Text(), nullable=True)
            )

        # Add scraped_at if not exists
        if 'scraped_at' not in existing_columns:
            op.add_column(
                'media',
                sa.Column('scraped_at', sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    """Remove provenance tracking columns from media table."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'media' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('media')]

        # Remove indexes first
        if 'source_url' in existing_columns:
            op.drop_index('ix_media_source_url', table_name='media')
        if 'source_name' in existing_columns:
            op.drop_index('ix_media_source_name', table_name='media')

        # Remove columns
        columns_to_remove = [
            'source_url', 'source_name', 'caption', 'rights_holder',
            'photographer', 'article_headline', 'article_summary', 'scraped_at'
        ]

        for col in columns_to_remove:
            if col in existing_columns:
                op.drop_column('media', col)
