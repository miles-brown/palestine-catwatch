"""Add merge tracking, name detection, and OCR fields

Revision ID: 004_add_merge_name
Revises: 003_add_provenance
Create Date: 2024-12-15

This migration adds:

Officers table:
- name: Officer name from uniform label (e.g., "PC WILLIAMS")
- ai_name: AI-detected name
- ai_name_confidence: Confidence score for AI name detection
- name_override: Manual name correction
- badge_override: Manual badge correction
- force_override: Manual force correction
- rank_override: Manual rank correction
- face_embedding: Face embedding for re-identification (LargeBinary)
- primary_crop_path: Best photo for display
- merged_into_id: Foreign key for merge tracking
- merge_confidence: Confidence that merge is correct
- merged_at: Timestamp when merged
- created_at: Creation timestamp
- updated_at: Last update timestamp

OfficerAppearance table:
- frame_number: Frame number in video
- face_embedding: Face embedding for this appearance (LargeBinary)
- ocr_badge_result: OCR-detected badge number
- ocr_badge_confidence: OCR confidence for badge
- ocr_name_result: OCR-detected name from uniform label
- ocr_name_confidence: OCR confidence for name
- ai_force: AI-detected police force
- ai_force_confidence: AI force confidence
- ai_rank: AI-detected rank
- ai_rank_confidence: AI rank confidence
- ai_name: AI-detected name
- ai_name_confidence: AI name confidence
- verified_at: When verified
- verified_by: Who verified (user FK)
- badge_override: Manual badge correction
- name_override: Manual name correction
- force_override: Manual force correction
- rank_override: Manual rank correction
- role_override: Manual role correction
- notes: Observer notes
- created_at: Creation timestamp
- updated_at: Last update timestamp

New tables:
- officer_merges: Tracks merge history for audit trail
- finalized_reports: Stores immutable report snapshots
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_merge_name'
down_revision: Union[str, None] = '003_add_provenance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add merge tracking and name detection fields."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # ========================================
    # Update officers table
    # ========================================
    if 'officers' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officers')]

        # Name detection fields
        if 'name' not in existing_columns:
            op.add_column('officers', sa.Column('name', sa.String(), nullable=True))
            op.create_index('ix_officers_name', 'officers', ['name'])

        if 'ai_name' not in existing_columns:
            op.add_column('officers', sa.Column('ai_name', sa.String(), nullable=True))

        if 'ai_name_confidence' not in existing_columns:
            op.add_column('officers', sa.Column('ai_name_confidence', sa.Float(), nullable=True))

        # Manual override fields
        if 'name_override' not in existing_columns:
            op.add_column('officers', sa.Column('name_override', sa.String(), nullable=True))

        if 'badge_override' not in existing_columns:
            op.add_column('officers', sa.Column('badge_override', sa.String(), nullable=True))

        if 'force_override' not in existing_columns:
            op.add_column('officers', sa.Column('force_override', sa.String(), nullable=True))

        if 'rank_override' not in existing_columns:
            op.add_column('officers', sa.Column('rank_override', sa.String(), nullable=True))

        # Face embedding for re-identification
        if 'face_embedding' not in existing_columns:
            op.add_column('officers', sa.Column('face_embedding', sa.LargeBinary(), nullable=True))

        # Best photo
        if 'primary_crop_path' not in existing_columns:
            op.add_column('officers', sa.Column('primary_crop_path', sa.String(), nullable=True))

        # Merge tracking
        if 'merged_into_id' not in existing_columns:
            op.add_column('officers', sa.Column('merged_into_id', sa.Integer(), nullable=True))
            # Note: Foreign key constraint added separately if needed

        if 'merge_confidence' not in existing_columns:
            op.add_column('officers', sa.Column('merge_confidence', sa.Float(), nullable=True))

        if 'merged_at' not in existing_columns:
            op.add_column('officers', sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True))

        # Timestamps
        if 'created_at' not in existing_columns:
            op.add_column('officers', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))

        if 'updated_at' not in existing_columns:
            op.add_column('officers', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # ========================================
    # Update officer_appearances table
    # ========================================
    if 'officer_appearances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officer_appearances')]

        # Frame tracking
        if 'frame_number' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('frame_number', sa.Integer(), nullable=True))

        # Face embedding
        if 'face_embedding' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('face_embedding', sa.LargeBinary(), nullable=True))

        # OCR badge results
        if 'ocr_badge_result' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ocr_badge_result', sa.String(), nullable=True))

        if 'ocr_badge_confidence' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ocr_badge_confidence', sa.Float(), nullable=True))

        # OCR name results
        if 'ocr_name_result' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ocr_name_result', sa.String(), nullable=True))

        if 'ocr_name_confidence' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ocr_name_confidence', sa.Float(), nullable=True))

        # AI detection results
        if 'ai_force' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_force', sa.String(), nullable=True))

        if 'ai_force_confidence' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_force_confidence', sa.Float(), nullable=True))

        if 'ai_rank' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_rank', sa.String(), nullable=True))

        if 'ai_rank_confidence' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_rank_confidence', sa.Float(), nullable=True))

        if 'ai_name' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_name', sa.String(), nullable=True))

        if 'ai_name_confidence' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('ai_name_confidence', sa.Float(), nullable=True))

        # Verification
        if 'verified_at' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))

        if 'verified_by' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('verified_by', sa.Integer(), nullable=True))

        # Manual overrides
        if 'badge_override' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('badge_override', sa.String(), nullable=True))

        if 'name_override' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('name_override', sa.String(), nullable=True))

        if 'force_override' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('force_override', sa.String(), nullable=True))

        if 'rank_override' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('rank_override', sa.String(), nullable=True))

        if 'role_override' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('role_override', sa.String(), nullable=True))

        if 'notes' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('notes', sa.Text(), nullable=True))

        # Timestamps
        if 'created_at' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))

        if 'updated_at' not in existing_columns:
            op.add_column('officer_appearances', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # ========================================
    # Create officer_merges table
    # ========================================
    if 'officer_merges' not in existing_tables:
        op.create_table(
            'officer_merges',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('primary_officer_id', sa.Integer(), sa.ForeignKey('officers.id'), index=True),
            sa.Column('merged_officer_id', sa.Integer(), sa.ForeignKey('officers.id'), index=True),
            sa.Column('merge_confidence', sa.Float(), nullable=True),
            sa.Column('auto_merged', sa.Boolean(), default=False),
            sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('merged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('unmerged', sa.Boolean(), default=False),
            sa.Column('unmerged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('unmerged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        )

    # ========================================
    # Create finalized_reports table
    # ========================================
    if 'finalized_reports' not in existing_tables:
        op.create_table(
            'finalized_reports',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('report_uuid', sa.String(), unique=True, index=True),
            sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id'), index=True),
            sa.Column('officers_data', sa.Text(), nullable=True),
            sa.Column('stats_data', sa.Text(), nullable=True),
            sa.Column('timeline_data', sa.Text(), nullable=True),
            sa.Column('title', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('finalized_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('pdf_path', sa.String(), nullable=True),
            sa.Column('pdf_generated_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove merge tracking and name detection fields."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Drop new tables
    if 'finalized_reports' in existing_tables:
        op.drop_table('finalized_reports')

    if 'officer_merges' in existing_tables:
        op.drop_table('officer_merges')

    # Remove columns from officer_appearances
    if 'officer_appearances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officer_appearances')]
        columns_to_remove = [
            'frame_number', 'face_embedding',
            'ocr_badge_result', 'ocr_badge_confidence',
            'ocr_name_result', 'ocr_name_confidence',
            'ai_force', 'ai_force_confidence',
            'ai_rank', 'ai_rank_confidence',
            'ai_name', 'ai_name_confidence',
            'verified_at', 'verified_by',
            'badge_override', 'name_override', 'force_override',
            'rank_override', 'role_override', 'notes',
            'created_at', 'updated_at'
        ]
        for col in columns_to_remove:
            if col in existing_columns:
                op.drop_column('officer_appearances', col)

    # Remove columns from officers
    if 'officers' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('officers')]

        # Drop index first
        if 'name' in existing_columns:
            try:
                op.drop_index('ix_officers_name', table_name='officers')
            except Exception:
                pass

        columns_to_remove = [
            'name', 'ai_name', 'ai_name_confidence',
            'name_override', 'badge_override', 'force_override', 'rank_override',
            'face_embedding', 'primary_crop_path',
            'merged_into_id', 'merge_confidence', 'merged_at',
            'created_at', 'updated_at'
        ]
        for col in columns_to_remove:
            if col in existing_columns:
                op.drop_column('officers', col)
