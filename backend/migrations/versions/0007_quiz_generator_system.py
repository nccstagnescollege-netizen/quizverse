"""Automatic Quiz and Question Paper Generator System

Revision ID: 0007_quiz_generator_system
Revises: 0006_bulk_import_export_system
Create Date: 2026-11-18 07:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007_quiz_generator_system'
down_revision: Union[str, None] = '0006_bulk_import_export_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Modify generation_history: make quiz_id nullable for pre-save drafts
    op.alter_column('generation_history', 'quiz_id',
                    existing_type=sa.Uuid(),
                    nullable=True)

    # 2. Add columns to generation_history
    op.add_column('generation_history', sa.Column('subject_id', sa.Uuid(), nullable=True))
    op.add_column('generation_history', sa.Column('session_title', sa.String(length=255), nullable=True))
    op.add_column('generation_history', sa.Column('academic_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('generation_history', sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('generation_history', sa.Column('exam_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('generation_history', sa.Column('selected_questions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('generation_history', sa.Column('validation_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('generation_history', sa.Column('seed', sa.String(length=64), nullable=True))
    op.add_column('generation_history', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # Foreign key for subject_id
    op.create_foreign_key(
        'fk_generation_history_subject_id',
        'generation_history', 'subjects',
        ['subject_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('ix_generation_history_subject_id', 'generation_history', ['subject_id'])
    op.create_index('ix_generation_history_generated_by', 'generation_history', ['generated_by'])

    # 3. Ensure permissions exist for quiz generation
    op.execute(sa.text("""
        INSERT INTO permissions (id, permission_name, description, created_at)
        VALUES 
            (gen_random_uuid(), 'quiz.generate', 'Generate automatic quiz and examination papers from question bank', now()),
            (gen_random_uuid(), 'question.answer.view', 'View correct answers and explanations for administrative question review and answer keys', now())
        ON CONFLICT (permission_name) DO NOTHING;
    """))


def downgrade() -> None:
    op.drop_constraint('fk_generation_history_subject_id', 'generation_history', type_='foreignkey')
    op.drop_index('ix_generation_history_subject_id', table_name='generation_history')
    op.drop_index('ix_generation_history_generated_by', table_name='generation_history')

    op.drop_column('generation_history', 'updated_at')
    op.drop_column('generation_history', 'seed')
    op.drop_column('generation_history', 'validation_report')
    op.drop_column('generation_history', 'selected_questions')
    op.drop_column('generation_history', 'exam_settings')
    op.drop_column('generation_history', 'configuration')
    op.drop_column('generation_history', 'academic_scope')
    op.drop_column('generation_history', 'session_title')
    op.drop_column('generation_history', 'subject_id')

    op.alter_column('generation_history', 'quiz_id',
                    existing_type=sa.Uuid(),
                    nullable=False)
