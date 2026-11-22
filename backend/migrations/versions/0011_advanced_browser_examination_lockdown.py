"""advanced_browser_examination_lockdown

Revision ID: 0011_advanced_browser_examination_lockdown
Revises: 0010_invitation_system_and_student_registration
Create Date: 2026-11-22 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0011_advanced_browser_examination_lockdown'
down_revision = '0010_invitation_system_and_student_registration'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Create browser_compatibility_records table
    op.create_table(
        'browser_compatibility_records',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=True),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=True),
        sa.Column('session_id', sa.String(length=128), nullable=True),
        sa.Column('browser_name', sa.String(length=64), nullable=False),
        sa.Column('browser_version', sa.String(length=64), nullable=False),
        sa.Column('os_name', sa.String(length=64), nullable=False),
        sa.Column('os_version', sa.String(length=64), nullable=False),
        sa.Column('device_type', sa.String(length=32), server_default=sa.text("'desktop'"), nullable=False),
        sa.Column('is_secure_context', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('javascript_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('fullscreen_supported', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('visibility_api_supported', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('storage_available', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('screen_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('screen_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('viewport_width', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('viewport_height', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('network_online', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('network_downlink', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('network_rtt', sa.Integer(), nullable=True),
        sa.Column('is_seb_detected', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('checks_summary', json_type, nullable=True),
        sa.Column('overall_status', sa.String(length=32), server_default=sa.text("'PASSED'"), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_browser_compatibility_records_attempt_id'), 'browser_compatibility_records', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_browser_compatibility_records_quiz_id'), 'browser_compatibility_records', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_browser_compatibility_records_student_id'), 'browser_compatibility_records', ['student_id'], unique=False)

    # 2. Add Phase 22 lockdown columns to quiz_configurations
    with op.batch_alter_table('quiz_configurations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fullscreen_exit_policy', sa.String(length=32), server_default=sa.text("'warning_only'"), nullable=False))
        batch_op.add_column(sa.Column('max_focus_loss_count', sa.Integer(), server_default=sa.text('5'), nullable=False))
        batch_op.add_column(sa.Column('disable_copy', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('disable_paste', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('disable_context_menu', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('print_restrictions', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('navigation_warning', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('network_interruption_policy', sa.String(length=32), server_default=sa.text("'buffer_and_resume'"), nullable=False))
        batch_op.add_column(sa.Column('require_invigilator_review', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    # 3. Add Phase 22 lockdown columns to examination_security_policies
    with op.batch_alter_table('examination_security_policies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fullscreen_exit_policy', sa.String(length=32), server_default=sa.text("'warning_only'"), nullable=False))
        batch_op.add_column(sa.Column('max_focus_loss_count', sa.Integer(), server_default=sa.text('5'), nullable=False))
        batch_op.add_column(sa.Column('disable_copy', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('disable_paste', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('disable_context_menu', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('print_restrictions', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('navigation_warning', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('network_interruption_policy', sa.String(length=32), server_default=sa.text("'buffer_and_resume'"), nullable=False))
        batch_op.add_column(sa.Column('require_invigilator_review', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade():
    with op.batch_alter_table('examination_security_policies', schema=None) as batch_op:
        batch_op.drop_column('require_invigilator_review')
        batch_op.drop_column('network_interruption_policy')
        batch_op.drop_column('navigation_warning')
        batch_op.drop_column('print_restrictions')
        batch_op.drop_column('disable_context_menu')
        batch_op.drop_column('disable_paste')
        batch_op.drop_column('disable_copy')
        batch_op.drop_column('max_focus_loss_count')
        batch_op.drop_column('fullscreen_exit_policy')

    with op.batch_alter_table('quiz_configurations', schema=None) as batch_op:
        batch_op.drop_column('require_invigilator_review')
        batch_op.drop_column('network_interruption_policy')
        batch_op.drop_column('navigation_warning')
        batch_op.drop_column('print_restrictions')
        batch_op.drop_column('disable_context_menu')
        batch_op.drop_column('disable_paste')
        batch_op.drop_column('disable_copy')
        batch_op.drop_column('max_focus_loss_count')
        batch_op.drop_column('fullscreen_exit_policy')

    op.drop_index(op.f('ix_browser_compatibility_records_student_id'), table_name='browser_compatibility_records')
    op.drop_index(op.f('ix_browser_compatibility_records_quiz_id'), table_name='browser_compatibility_records')
    op.drop_index(op.f('ix_browser_compatibility_records_attempt_id'), table_name='browser_compatibility_records')
    op.drop_table('browser_compatibility_records')
