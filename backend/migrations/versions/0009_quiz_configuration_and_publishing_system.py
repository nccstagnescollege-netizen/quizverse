"""quiz_configuration_and_publishing_system

Revision ID: 0009_quiz_configuration_and_publishing_system
Revises: 0008_manual_quiz_creator_system
Create Date: 2026-11-18 19:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009_quiz_configuration_and_publishing_system'
down_revision = '0008_manual_quiz_creator_system'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Add published_version & validation status columns to `quizzes` if not present
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('published_version', sa.Integer(), server_default=sa.text('0'), nullable=False))
        batch_op.add_column(sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('validation_summary', json_type, nullable=True))

    # 2. Create `quiz_configurations` table
    op.create_table(
        'quiz_configurations',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        
        # Timing & Schedule
        sa.Column('timezone', sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
        sa.Column('availability_mode', sa.String(length=32), server_default=sa.text("'immediate'"), nullable=False), # immediate, scheduled, restricted
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reading_time_minutes', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('accommodations_extra_minutes', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('late_entry_minutes', sa.Integer(), nullable=True),
        sa.Column('early_access_minutes', sa.Integer(), nullable=True),
        sa.Column('grace_period_minutes', sa.Integer(), server_default=sa.text('5'), nullable=False),
        sa.Column('timer_type', sa.String(length=32), server_default=sa.text("'per_student'"), nullable=False), # per_student, server_window

        # Question Policies & Randomization
        sa.Column('shuffle_questions', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('shuffle_options', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('question_grouping', sa.String(length=32), server_default=sa.text("'preserve_order'"), nullable=False), # preserve_order, randomize_within_sections, fixed
        sa.Column('question_selection_mode', sa.String(length=32), server_default=sa.text("'all_questions'"), nullable=False), # all_questions, section_rules

        # Scoring & Evaluation
        sa.Column('passing_criteria_type', sa.String(length=32), server_default=sa.text("'percentage'"), nullable=False), # percentage, fixed_marks
        sa.Column('passing_marks', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('passing_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('40.00'), nullable=False),
        sa.Column('negative_marking_type', sa.String(length=32), server_default=sa.text("'none'"), nullable=False), # none, fixed, question_specific
        sa.Column('fixed_negative_marks', sa.Numeric(precision=6, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('partial_marking_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('rounding_precision', sa.Integer(), server_default=sa.text('2'), nullable=False),
        sa.Column('evaluation_method', sa.String(length=32), server_default=sa.text("'automatic'"), nullable=False), # automatic, manual, mixed
        sa.Column('require_manual_evaluation', sa.Boolean(), server_default=sa.text('false'), nullable=False),

        # Student Navigation
        sa.Column('navigation_mode', sa.String(length=32), server_default=sa.text("'free'"), nullable=False), # free, sequential
        sa.Column('allow_previous_nav', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('allow_answer_change', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('allow_mark_for_review', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('allow_skip_questions', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_question_palette', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_answered_stats', sa.Boolean(), server_default=sa.text('true'), nullable=False),

        # Submission Policies
        sa.Column('manual_submission_allowed', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('auto_submit_on_timeout', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('submission_confirmation_modal', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('submit_unanswered_questions', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('allow_attempt_reentry_on_disconnect', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('reentry_grace_minutes', sa.Integer(), server_default=sa.text('15'), nullable=False),

        # Student Access Conditions (Phase 11 prep)
        sa.Column('registration_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('account_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('one_attempt_per_student', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('allow_multiple_devices', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('require_invitation', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('restricted_student_groups', json_type, server_default=sa.text("'[]'"), nullable=False),

        # Result Visibility Policies
        sa.Column('result_release_policy', sa.String(length=32), server_default=sa.text("'immediate'"), nullable=False), # immediate, after_close, after_manual_eval, after_admin_approval, never
        sa.Column('show_score_immediately', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_correct_answers', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('show_answer_keys', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('show_explanations', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('show_section_breakdown', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_final_status_pass_fail', sa.Boolean(), server_default=sa.text('true'), nullable=False),

        # Examination Security Policies
        sa.Column('log_focus_loss', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('log_copy_paste', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('enforce_fullscreen', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('watermark_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('concurrent_session_block', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('suspicious_activity_flagging', sa.Boolean(), server_default=sa.text('true'), nullable=False),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], name='fk_quiz_configurations_quiz_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', name='uq_quiz_configurations_quiz_id')
    )
    op.create_index('ix_quiz_configurations_quiz_id', 'quiz_configurations', ['quiz_id'])

    # 3. Create `quiz_published_versions` table
    op.create_table(
        'quiz_published_versions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('published_by', sa.Uuid(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('snapshot_data', json_type, nullable=False), # Frozen snapshot of quiz, sections, questions, and configurations
        sa.Column('validation_report', json_type, nullable=True),
        sa.Column('change_log', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], name='fk_quiz_published_versions_quiz_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by'], ['admins.id'], name='fk_quiz_published_versions_published_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'version_number', name='uq_quiz_published_versions_quiz_version')
    )
    op.create_index('ix_quiz_published_versions_quiz_id', 'quiz_published_versions', ['quiz_id'])

    # 4. Create `quiz_publishing_history` table
    op.create_table(
        'quiz_publishing_history',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(length=32), nullable=False),
        sa.Column('to_status', sa.String(length=32), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False), # publish, schedule, unpublish, archive, cancel, validate
        sa.Column('performed_by', sa.Uuid(), nullable=True),
        sa.Column('reason', sa.String(length=512), nullable=True),
        sa.Column('metadata_snapshot', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], name='fk_quiz_publishing_history_quiz_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by'], ['admins.id'], name='fk_quiz_publishing_history_performed_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_publishing_history_quiz_id', 'quiz_publishing_history', ['quiz_id'])


def downgrade():
    op.drop_index('ix_quiz_publishing_history_quiz_id', table_name='quiz_publishing_history')
    op.drop_table('quiz_publishing_history')

    op.drop_index('ix_quiz_published_versions_quiz_id', table_name='quiz_published_versions')
    op.drop_table('quiz_published_versions')

    op.drop_index('ix_quiz_configurations_quiz_id', table_name='quiz_configurations')
    op.drop_table('quiz_configurations')

    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_column('validation_summary')
        batch_op.drop_column('last_validated_at')
        batch_op.drop_column('published_version')
