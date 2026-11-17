"""Complete PostgreSQL database architecture

Revision ID: 0002_complete_database_schema
Revises: 0001_initial_baseline
Create Date: 2026-11-17 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_complete_database_schema'
down_revision: Union[str, None] = '0001_initial_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Admins
    op.create_table(
        'admins',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auth_user_id', sa.Uuid(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_admins_email')
    )
    op.create_index('ix_admins_auth_user_id', 'admins', ['auth_user_id'], unique=True)
    op.create_index('ix_admins_email', 'admins', ['email'])

    # 2. Roles
    op.create_table(
        'roles',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('role_name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_name', name='uq_roles_role_name')
    )
    op.create_index('ix_roles_role_name', 'roles', ['role_name'])

    # 3. Permissions
    op.create_table(
        'permissions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('permission_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('permission_name', name='uq_permissions_name')
    )
    op.create_index('ix_permissions_permission_name', 'permissions', ['permission_name'])

    # 4. Admin Roles
    op.create_table(
        'admin_roles',
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('admin_id', 'role_id')
    )

    # 5. Role Permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('permission_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # 6. Units
    op.create_table(
        'units',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('unit_name', sa.String(length=255), nullable=False),
        sa.Column('unit_code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unit_code', name='uq_units_unit_code')
    )
    op.create_index('ix_units_unit_code', 'units', ['unit_code'])

    # 7. Chapters
    op.create_table(
        'chapters',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('unit_id', sa.Uuid(), nullable=False),
        sa.Column('chapter_name', sa.String(length=255), nullable=False),
        sa.Column('chapter_code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unit_id', 'chapter_code', name='uq_chapters_unit_code')
    )
    op.create_index('ix_chapters_unit_id', 'chapters', ['unit_id'])

    # 8. Topics
    op.create_table(
        'topics',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('chapter_id', sa.Uuid(), nullable=False),
        sa.Column('topic_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topics_chapter_id', 'topics', ['chapter_id'])

    # 9. Questions
    op.create_table(
        'questions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('topic_id', sa.Uuid(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=32), server_default=sa.text("'single_choice'"), nullable=False),
        sa.Column('difficulty', sa.String(length=32), server_default=sa.text("'medium'"), nullable=False),
        sa.Column('default_marks', sa.Numeric(precision=6, scale=2), server_default=sa.text('1.00'), nullable=False),
        sa.Column('default_negative_marks', sa.Numeric(precision=6, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('question_image_path', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('default_marks >= 0', name='chk_question_default_marks_positive'),
        sa.CheckConstraint('default_negative_marks >= 0', name='chk_question_negative_marks_positive'),
        sa.ForeignKeyConstraint(['created_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_questions_topic_id', 'questions', ['topic_id'])
    op.create_index('ix_questions_status', 'questions', ['status'])
    op.create_index('ix_questions_difficulty', 'questions', ['difficulty'])

    # 10. Question Options
    op.create_table(
        'question_options',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('option_image_path', sa.String(length=512), nullable=True),
        sa.Column('option_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_correct', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_options_question_id', 'question_options', ['question_id'])

    # 11. Question Tags
    op.create_table(
        'question_tags',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tag_name', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag_name', name='uq_question_tags_name')
    )
    op.create_index('ix_question_tags_tag_name', 'question_tags', ['tag_name'])

    # 12. Question Tag Relations
    op.create_table(
        'question_tag_relations',
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('tag_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['question_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('question_id', 'tag_id')
    )

    # 13. Question Versions
    op.create_table(
        'question_versions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('question_snapshot', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('changed_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', 'version_number', name='uq_question_versions_num')
    )
    op.create_index('ix_question_versions_question_id', 'question_versions', ['question_id'])

    # 14. Quizzes
    op.create_table(
        'quizzes',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), server_default=sa.text('60'), nullable=False),
        sa.Column('total_marks', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('passing_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('40.00'), nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('shuffle_questions', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('shuffle_options', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_results_immediately', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('show_correct_answers', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('allow_review', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('duration_minutes > 0', name='chk_quiz_duration_positive'),
        sa.CheckConstraint('passing_percentage >= 0 AND passing_percentage <= 100', name='chk_quiz_passing_percentage_valid'),
        sa.CheckConstraint('max_attempts >= 1', name='chk_quiz_max_attempts_valid'),
        sa.ForeignKeyConstraint(['created_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_quizzes_slug')
    )
    op.create_index('ix_quizzes_slug', 'quizzes', ['slug'])
    op.create_index('ix_quizzes_status', 'quizzes', ['status'])

    # 15. Quiz Questions
    op.create_table(
        'quiz_questions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('question_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('marks', sa.Numeric(precision=6, scale=2), server_default=sa.text('1.00'), nullable=False),
        sa.Column('negative_marks', sa.Numeric(precision=6, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('question_snapshot', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('marks >= 0', name='chk_quiz_question_marks_positive'),
        sa.CheckConstraint('negative_marks >= 0', name='chk_quiz_question_neg_marks_positive'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'question_id', name='uq_quiz_questions_quiz_question')
    )
    op.create_index('ix_quiz_questions_quiz_id', 'quiz_questions', ['quiz_id'])
    op.create_index('ix_quiz_questions_question_id', 'quiz_questions', ['question_id'])

    # 16. Quiz Generation Rules
    op.create_table(
        'quiz_generation_rules',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('rule_name', sa.String(length=255), nullable=False),
        sa.Column('target_topic_ids', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('easy_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('medium_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('hard_percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('total_questions_target', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('total_questions_target > 0', name='chk_quiz_gen_rule_total_positive'),
        sa.CheckConstraint(
            '(easy_percentage + medium_percentage + hard_percentage) >= 99.99 AND (easy_percentage + medium_percentage + hard_percentage) <= 100.01',
            name='chk_quiz_gen_rule_diff_sum_100'
        ),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_generation_rules_quiz_id', 'quiz_generation_rules', ['quiz_id'])

    # 17. Generation History
    op.create_table(
        'generation_history',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('rule_id', sa.Uuid(), nullable=True),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('generated_by', sa.Uuid(), nullable=True),
        sa.Column('questions_selected_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('generation_rule_snapshot', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'success'"), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['quiz_generation_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generation_history_quiz_id', 'generation_history', ['quiz_id'])

    # 18. Students
    op.create_table(
        'students',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auth_user_id', sa.Uuid(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('is_guest', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_students_email')
    )
    op.create_index('ix_students_auth_user_id', 'students', ['auth_user_id'], unique=True)
    op.create_index('ix_students_email', 'students', ['email'])

    # 19. Student Profiles
    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.Column('institution', sa.String(length=255), nullable=True),
        sa.Column('student_identifier', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', name='uq_student_profiles_student_id')
    )
    op.create_index('ix_student_profiles_student_id', 'student_profiles', ['student_id'])

    # 20. Registration Form Fields
    op.create_table(
        'registration_form_fields',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('field_label', sa.String(length=255), nullable=False),
        sa.Column('field_name', sa.String(length=64), nullable=False),
        sa.Column('field_type', sa.String(length=32), server_default=sa.text("'text'"), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('validation_rules', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'field_name', name='uq_reg_field_quiz_name')
    )
    op.create_index('ix_registration_form_fields_quiz_id', 'registration_form_fields', ['quiz_id'])

    # 21. Registration Submissions
    op.create_table(
        'registration_submissions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('submitted_data', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'student_id', name='uq_reg_sub_quiz_student')
    )
    op.create_index('ix_registration_submissions_quiz_id', 'registration_submissions', ['quiz_id'])
    op.create_index('ix_registration_submissions_student_id', 'registration_submissions', ['student_id'])

    # 22. Invitation Links
    op.create_table(
        'invitation_links',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('target_email', sa.String(length=255), nullable=True),
        sa.Column('max_uses', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('used_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('max_uses >= 1', name='chk_invitation_max_uses_valid'),
        sa.CheckConstraint('used_count >= 0', name='chk_invitation_used_count_positive'),
        sa.ForeignKeyConstraint(['created_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_invitation_links_token_hash')
    )
    op.create_index('ix_invitation_links_quiz_id', 'invitation_links', ['quiz_id'])
    op.create_index('ix_invitation_links_token_hash', 'invitation_links', ['token_hash'])

    # 23. Invitation Usage
    op.create_table(
        'invitation_usage',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('invitation_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['invitation_id'], ['invitation_links.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invitation_id', 'student_id', name='uq_invitation_usage_inv_student')
    )
    op.create_index('ix_invitation_usage_invitation_id', 'invitation_usage', ['invitation_id'])
    op.create_index('ix_invitation_usage_student_id', 'invitation_usage', ['student_id'])

    # 24. Examination Attempts
    op.create_table(
        'examination_attempts',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'in_progress'"), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('attempt_number >= 1', name='chk_exam_attempt_number_positive'),
        sa.CheckConstraint('time_spent_seconds >= 0', name='chk_exam_attempt_time_spent_positive'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'student_id', 'attempt_number', name='uq_exam_attempt_quiz_student_num')
    )
    op.create_index('ix_examination_attempts_quiz_id', 'examination_attempts', ['quiz_id'])
    op.create_index('ix_examination_attempts_student_id', 'examination_attempts', ['student_id'])
    op.create_index('ix_examination_attempts_status', 'examination_attempts', ['status'])

    # 25. Attempt Answers
    op.create_table(
        'attempt_answers',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_question_id', sa.Uuid(), nullable=False),
        sa.Column('selected_option_ids', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('text_response', sa.Text(), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_flagged_for_review', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('time_spent_seconds >= 0', name='chk_attempt_answer_time_positive'),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_question_id'], ['quiz_questions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', 'quiz_question_id', name='uq_attempt_answers_attempt_qq')
    )
    op.create_index('ix_attempt_answers_attempt_id', 'attempt_answers', ['attempt_id'])

    # 26. Attempt Events
    op.create_table(
        'attempt_events',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('event_metadata', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_attempt_events_attempt_id', 'attempt_events', ['attempt_id'])

    # 27. Examination Results
    op.create_table(
        'examination_results',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('score', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('is_passed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('total_correct', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_incorrect', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_unanswered', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('percentile', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', name='uq_examination_results_attempt_id')
    )
    op.create_index('ix_examination_results_quiz_id', 'examination_results', ['quiz_id'])
    op.create_index('ix_examination_results_student_id', 'examination_results', ['student_id'])

    # 28. Question Evaluations
    op.create_table(
        'question_evaluations',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('result_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_question_id', sa.Uuid(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_partially_correct', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('marks_awarded', sa.Numeric(precision=6, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_question_id'], ['quiz_questions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['result_id'], ['examination_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('result_id', 'quiz_question_id', name='uq_q_eval_result_qq')
    )
    op.create_index('ix_question_evaluations_result_id', 'question_evaluations', ['result_id'])

    # 29. Analytics Snapshots
    op.create_table(
        'analytics_snapshots',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('total_participants', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('average_score', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('highest_score', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('lowest_score', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('median_score', sa.Numeric(precision=8, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('pass_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('fail_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('topic_performances', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('question_breakdowns', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_analytics_snapshots_quiz_id', 'analytics_snapshots', ['quiz_id'])

    # 30. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('details', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_admin_id', 'audit_logs', ['admin_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])

    # 31. Security Events
    op.create_table(
        'security_events',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=True),
        sa.Column('attempt_id', sa.Uuid(), nullable=True),
        sa.Column('severity', sa.String(length=32), server_default=sa.text("'info'"), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_events_severity', 'security_events', ['severity'])
    op.create_index('ix_security_events_event_name', 'security_events', ['event_name'])

    # 32. Access Logs
    op.create_table(
        'access_logs',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('user_type', sa.String(length=32), server_default=sa.text("'guest'"), nullable=False),
        sa.Column('endpoint', sa.String(length=512), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_access_logs_user_id', 'access_logs', ['user_id'])
    op.create_index('ix_access_logs_created_at', 'access_logs', ['created_at'])

    # 33. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('recipient_type', sa.String(length=32), nullable=False),
        sa.Column('recipient_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=64), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_recipient', 'notifications', ['recipient_type', 'recipient_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])

    # 34. Notification Preferences
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('recipient_type', sa.String(length=32), nullable=False),
        sa.Column('recipient_id', sa.Uuid(), nullable=False),
        sa.Column('email_notifications', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('in_app_notifications', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('security_alerts', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipient_type', 'recipient_id', name='uq_notif_pref_recipient')
    )
    op.create_index('ix_notification_preferences_recipient', 'notification_preferences', ['recipient_type', 'recipient_id'])

    # PostgreSQL specific: Row Level Security & Policies
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        all_tables = [
            'admins', 'roles', 'permissions', 'admin_roles', 'role_permissions',
            'units', 'chapters', 'topics', 'questions', 'question_options',
            'question_tags', 'question_tag_relations', 'question_versions',
            'quizzes', 'quiz_questions', 'quiz_generation_rules', 'generation_history',
            'students', 'student_profiles', 'registration_form_fields',
            'registration_submissions', 'invitation_links', 'invitation_usage',
            'examination_attempts', 'attempt_answers', 'attempt_events',
            'examination_results', 'question_evaluations', 'analytics_snapshots',
            'audit_logs', 'security_events', 'access_logs', 'notifications',
            'notification_preferences'
        ]

        # Enable RLS on every table
        for tbl in all_tables:
            op.execute(sa.text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY"))

        # Baseline Security Policies
        op.execute(sa.text("""
            -- Helper function for checking admin status safely
            CREATE OR REPLACE FUNCTION public.is_active_admin()
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN EXISTS (
                    SELECT 1 FROM public.admins
                    WHERE auth_user_id = auth.uid() AND status = 'active'
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;

            -- Admins have full access to management tables
            CREATE POLICY admin_full_access_admins ON admins FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_roles ON roles FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_units ON units FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_chapters ON chapters FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_topics ON topics FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_questions ON questions FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_quizzes ON quizzes FOR ALL TO authenticated
                USING (public.is_active_admin());

            CREATE POLICY admin_full_access_audit_logs ON audit_logs FOR ALL TO authenticated
                USING (public.is_active_admin());

            -- Public & Student access to published quizzes (read-only)
            CREATE POLICY student_select_published_quizzes ON quizzes FOR SELECT
                USING (status = 'published');

            -- Students can view their own profile
            CREATE POLICY student_self_profile ON student_profiles FOR ALL TO authenticated
                USING (student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid()));

            -- Students can view and submit their own attempts
            CREATE POLICY student_self_attempts ON examination_attempts FOR ALL TO authenticated
                USING (student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid()));

            -- Students can record/view their own answers
            CREATE POLICY student_self_answers ON attempt_answers FOR ALL TO authenticated
                USING (attempt_id IN (
                    SELECT id FROM examination_attempts
                    WHERE student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid())
                ));

            -- Students can view their own examination results
            CREATE POLICY student_self_results ON examination_results FOR SELECT TO authenticated
                USING (student_id IN (SELECT id FROM students WHERE auth_user_id = auth.uid()));
        """))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text("DROP FUNCTION IF EXISTS public.is_active_admin() CASCADE;"))

    tables_in_reverse = [
        'notification_preferences',
        'notifications',
        'access_logs',
        'security_events',
        'audit_logs',
        'analytics_snapshots',
        'question_evaluations',
        'examination_results',
        'attempt_events',
        'attempt_answers',
        'examination_attempts',
        'invitation_usage',
        'invitation_links',
        'registration_submissions',
        'registration_form_fields',
        'student_profiles',
        'students',
        'generation_history',
        'quiz_generation_rules',
        'quiz_questions',
        'quizzes',
        'question_versions',
        'question_tag_relations',
        'question_tags',
        'question_options',
        'questions',
        'topics',
        'chapters',
        'units',
        'role_permissions',
        'admin_roles',
        'permissions',
        'roles',
        'admins'
    ]

    for tbl in tables_in_reverse:
        op.drop_table(tbl)
