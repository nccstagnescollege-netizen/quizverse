"""invitation_system_and_student_registration

Revision ID: 0010_invitation_system_and_student_registration
Revises: 0009_quiz_configuration_and_publishing_system
Create Date: 2026-11-18 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010_invitation_system_and_student_registration'
down_revision = '0009_quiz_configuration_and_publishing_system'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Enhance invitation_links table
    with op.batch_alter_table('invitation_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=255), server_default=sa.text("'General Invitation'"), nullable=False))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('invitation_type', sa.String(length=32), server_default=sa.text("'general'"), nullable=False))
        batch_op.add_column(sa.Column('category', sa.String(length=64), server_default=sa.text("'Regular'"), nullable=False))
        batch_op.add_column(sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False))
        batch_op.add_column(sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('timezone', sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False))
        batch_op.add_column(sa.Column('max_attempts_per_student', sa.Integer(), server_default=sa.text('1'), nullable=False))
        batch_op.add_column(sa.Column('allowed_student_groups', json_type, nullable=True))
        batch_op.add_column(sa.Column('is_reusable', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('require_account', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('require_approval', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('internal_notes', sa.Text(), nullable=True))

    # 2. Enhance invitation_usage table
    with op.batch_alter_table('invitation_usage', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=32), server_default=sa.text("'success'"), nullable=False))
        batch_op.add_column(sa.Column('failure_reason', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('device_type', sa.String(length=32), nullable=True))

    # 3. Create quiz_registration_forms table
    op.create_table(
        'quiz_registration_forms',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('title', sa.String(length=255), server_default=sa.text("'Student Registration Form'"), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fields_config', json_type, nullable=False),
        sa.Column('unique_fields', json_type, nullable=False),
        sa.Column('require_manual_approval', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'version_number', name='uq_quiz_reg_form_version')
    )
    op.create_index('ix_quiz_registration_forms_quiz_id', 'quiz_registration_forms', ['quiz_id'])

    # 4. Create quiz_participants table
    op.create_table(
        'quiz_participants',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('invitation_id', sa.Uuid(), nullable=True),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('form_version_id', sa.Uuid(), nullable=True),
        sa.Column('registration_data', json_type, nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'approved'"), nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['form_version_id'], ['quiz_registration_forms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invitation_id'], ['invitation_links.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quiz_id', 'student_id', name='uq_quiz_participant_quiz_student')
    )
    op.create_index('ix_quiz_participants_quiz_id', 'quiz_participants', ['quiz_id'])
    op.create_index('ix_quiz_participants_invitation_id', 'quiz_participants', ['invitation_id'])
    op.create_index('ix_quiz_participants_student_id', 'quiz_participants', ['student_id'])
    op.create_index('ix_quiz_participants_status', 'quiz_participants', ['status'])


def downgrade():
    op.drop_index('ix_quiz_participants_status', table_name='quiz_participants')
    op.drop_index('ix_quiz_participants_student_id', table_name='quiz_participants')
    op.drop_index('ix_quiz_participants_invitation_id', table_name='quiz_participants')
    op.drop_index('ix_quiz_participants_quiz_id', table_name='quiz_participants')
    op.drop_table('quiz_participants')

    op.drop_index('ix_quiz_registration_forms_quiz_id', table_name='quiz_registration_forms')
    op.drop_table('quiz_registration_forms')

    with op.batch_alter_table('invitation_usage', schema=None) as batch_op:
        batch_op.drop_column('device_type')
        batch_op.drop_column('failure_reason')
        batch_op.drop_column('status')

    with op.batch_alter_table('invitation_links', schema=None) as batch_op:
        batch_op.drop_column('internal_notes')
        batch_op.drop_column('require_approval')
        batch_op.drop_column('require_account')
        batch_op.drop_column('is_reusable')
        batch_op.drop_column('allowed_student_groups')
        batch_op.drop_column('max_attempts_per_student')
        batch_op.drop_column('timezone')
        batch_op.drop_column('starts_at')
        batch_op.drop_column('status')
        batch_op.drop_column('category')
        batch_op.drop_column('invitation_type')
        batch_op.drop_column('description')
        batch_op.drop_column('name')
