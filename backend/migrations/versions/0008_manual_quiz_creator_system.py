"""manual_quiz_creator_system

Revision ID: 0008_manual_quiz_creator_system
Revises: 0007_quiz_generator_system
Create Date: 2026-11-18 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '0008_manual_quiz_creator_system'
down_revision = '0007_quiz_generator_system'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Add manual authoring columns to `quizzes`
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('institution_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('programme_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('academic_session_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('semester_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('subject_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('reference_code', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('cover_image_url', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('academic_scope', json_type, nullable=True))
        batch_op.add_column(sa.Column('scoring_policy', json_type, nullable=True))
        batch_op.add_column(sa.Column('creation_mode', sa.String(length=32), server_default=sa.text("'manual'"), nullable=False))
        batch_op.add_column(sa.Column('is_draft', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('draft_version', sa.Integer(), server_default=sa.text('1'), nullable=False))

        batch_op.create_foreign_key('fk_quizzes_institution_id', 'institutions', ['institution_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_quizzes_programme_id', 'programmes', ['programme_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_quizzes_academic_session_id', 'academic_sessions', ['academic_session_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_quizzes_semester_id', 'semesters', ['semester_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_quizzes_subject_id', 'subjects', ['subject_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_quizzes_subject_id', ['subject_id'])

    # 2. Create `quiz_sections` table
    op.create_table(
        'quiz_sections',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('section_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('selection_rule', sa.String(length=64), server_default=sa.text("'all_compulsory'"), nullable=False),
        sa.Column('required_question_count', sa.Integer(), nullable=True),
        sa.Column('total_questions_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('default_marks_per_question', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('default_negative_marks_per_question', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('section_total_marks', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_sections_quiz_id', 'quiz_sections', ['quiz_id'])

    # 3. Update `quiz_questions` table for manual creation and section mapping
    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.alter_column('question_id', existing_type=sa.Uuid(), nullable=True)
        batch_op.add_column(sa.Column('section_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('is_compulsory', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('is_manual', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('source_type', sa.String(length=32), server_default=sa.text("'bank'"), nullable=False))
        batch_op.add_column(sa.Column('custom_instructions', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('scoring_settings', json_type, nullable=True))

        batch_op.create_foreign_key('fk_quiz_questions_section_id', 'quiz_sections', ['section_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_quiz_questions_section_id', ['section_id'])

    # 4. Create `quiz_draft_versions` table
    op.create_table(
        'quiz_draft_versions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('saved_by', sa.Uuid(), nullable=True),
        sa.Column('snapshot_data', json_type, nullable=False),
        sa.Column('change_summary', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['saved_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_draft_versions_quiz_id', 'quiz_draft_versions', ['quiz_id'])

    # 5. Create `quiz_attachments` table
    op.create_table(
        'quiz_attachments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_question_id', sa.Uuid(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_type', sa.String(length=128), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_question_id'], ['quiz_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_attachments_quiz_id', 'quiz_attachments', ['quiz_id'])
    op.create_index('ix_quiz_attachments_quiz_question_id', 'quiz_attachments', ['quiz_question_id'])

    # Ensure alembic_version has sufficient length for subsequent revision 0009
    try:
        op.execute(sa.text("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE character varying(128);"))
    except Exception:
        pass


def downgrade():
    op.drop_table('quiz_attachments')
    op.drop_table('quiz_draft_versions')

    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_quiz_questions_section_id', type_='foreignkey')
        batch_op.drop_index('ix_quiz_questions_section_id')
        batch_op.drop_column('scoring_settings')
        batch_op.drop_column('custom_instructions')
        batch_op.drop_column('source_type')
        batch_op.drop_column('is_manual')
        batch_op.drop_column('is_compulsory')
        batch_op.drop_column('section_id')
        batch_op.alter_column('question_id', existing_type=sa.Uuid(), nullable=False)

    op.drop_table('quiz_sections')

    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_index('ix_quizzes_subject_id')
        batch_op.drop_constraint('fk_quizzes_subject_id', type_='foreignkey')
        batch_op.drop_constraint('fk_quizzes_semester_id', type_='foreignkey')
        batch_op.drop_constraint('fk_quizzes_academic_session_id', type_='foreignkey')
        batch_op.drop_constraint('fk_quizzes_programme_id', type_='foreignkey')
        batch_op.drop_constraint('fk_quizzes_institution_id', type_='foreignkey')

        batch_op.drop_column('draft_version')
        batch_op.drop_column('is_draft')
        batch_op.drop_column('creation_mode')
        batch_op.drop_column('scoring_policy')
        batch_op.drop_column('academic_scope')
        batch_op.drop_column('cover_image_url')
        batch_op.drop_column('reference_code')
        batch_op.drop_column('category')
        batch_op.drop_column('subject_id')
        batch_op.drop_column('semester_id')
        batch_op.drop_column('academic_session_id')
        batch_op.drop_column('programme_id')
        batch_op.drop_column('institution_id')
