"""Bulk question import, validation, export and file management

Revision ID: 0006_bulk_import_export_system
Revises: 0005_question_bank_system
Create Date: 2026-11-17 23:45:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006_bulk_import_export_system'
down_revision: Union[str, None] = '0005_question_bank_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure question_tags has description column and question_versions has change_summary
    op.execute(sa.text("ALTER TABLE question_tags ADD COLUMN IF NOT EXISTS description TEXT;"))
    op.execute(sa.text("ALTER TABLE question_versions ADD COLUMN IF NOT EXISTS change_summary TEXT;"))

    # 1. Add external_id column to questions
    op.add_column('questions', sa.Column('external_id', sa.String(length=128), nullable=True))
    op.create_index('ix_questions_external_id', 'questions', ['external_id'])

    # 2. question_import_jobs table
    op.create_table(
        'question_import_jobs',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_format', sa.String(length=16), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('file_checksum', sa.String(length=64), nullable=True),
        sa.Column('template_version', sa.String(length=32), server_default=sa.text("'v1.0'"), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'uploaded'"), nullable=False),
        sa.Column('total_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('valid_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('invalid_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('warning_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('duplicate_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('imported_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('skipped_rows', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('import_policy', sa.String(length=32), server_default=sa.text("'import_valid'"), nullable=False),
        sa.Column('duplicate_strategy', sa.String(length=32), server_default=sa.text("'skip'"), nullable=False),
        sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('summary_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['admins.id'], name='fk_question_import_jobs_uploaded_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_import_jobs_uploaded_by', 'question_import_jobs', ['uploaded_by'])
    op.create_index('ix_question_import_jobs_status', 'question_import_jobs', ['status'])
    op.create_index('ix_question_import_jobs_created_at', 'question_import_jobs', ['created_at'])

    # 3. question_import_rows table
    op.create_table(
        'question_import_rows',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_status', sa.String(length=32), server_default=sa.text("'valid'"), nullable=False),
        sa.Column('is_duplicate', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('duplicate_question_id', sa.Uuid(), nullable=True),
        sa.Column('imported_question_id', sa.Uuid(), nullable=True),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['question_import_jobs.id'], name='fk_question_import_rows_job', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['duplicate_question_id'], ['questions.id'], name='fk_question_import_rows_dup_q', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['imported_question_id'], ['questions.id'], name='fk_question_import_rows_imp_q', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_import_rows_job_id', 'question_import_rows', ['job_id'])
    op.create_index('ix_question_import_rows_validation_status', 'question_import_rows', ['validation_status'])
    op.create_index('ix_question_import_rows_row_number', 'question_import_rows', ['row_number'])

    # 4. question_export_jobs table
    op.create_table(
        'question_export_jobs',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('requested_by', sa.Uuid(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('export_format', sa.String(length=16), nullable=False),
        sa.Column('export_mode', sa.String(length=32), server_default=sa.text("'question_only'"), nullable=False),
        sa.Column('filters_applied', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_questions', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'completed'"), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['requested_by'], ['admins.id'], name='fk_question_export_jobs_requested_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_export_jobs_requested_by', 'question_export_jobs', ['requested_by'])
    op.create_index('ix_question_export_jobs_status', 'question_export_jobs', ['status'])

    # 5. Insert question.import.review permission if not present
    op.execute("""
        INSERT INTO permissions (id, permission_name, description, created_at)
        VALUES (gen_random_uuid(), 'question.import.review', 'Permission to review and validate imported questions', NOW())
        ON CONFLICT (permission_name) DO NOTHING;
    """)

    # Grant new permission to super_admin and user_admin
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.role_name IN ('super_admin', 'user_admin')
          AND p.permission_name = 'question.import.review'
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('question_export_jobs')
    op.drop_table('question_import_rows')
    op.drop_table('question_import_jobs')
    op.drop_index('ix_questions_external_id', table_name='questions')
    op.drop_column('questions', 'external_id')
