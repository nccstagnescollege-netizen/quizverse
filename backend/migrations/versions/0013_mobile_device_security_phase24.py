"""mobile_device_security_phase24

Revision ID: 0013_mobile_device_security_phase24
Revises: 0012_screenshot_screen_recording_watermark_phase23
Create Date: 2026-11-22 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0013_mobile_device_security_phase24'
down_revision = '0012_screenshot_screen_recording_watermark_phase23'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Add Phase 24 columns to quiz_configurations
    op.add_column('quiz_configurations', sa.Column('require_native_app', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('android_secure_mode', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('ios_secure_mode', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('require_kiosk_mode', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('min_android_version', sa.Integer(), server_default=sa.text('26'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('min_ios_version', sa.String(length=32), server_default=sa.text("'15.0'"), nullable=False))
    op.add_column('quiz_configurations', sa.Column('mobile_interruption_policy', sa.String(length=32), server_default=sa.text("'allow_with_event'"), nullable=False))
    op.add_column('quiz_configurations', sa.Column('allow_device_recovery', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('block_rooted_devices', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # 2. Create device_registrations table
    op.create_table(
        'device_registrations',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=128), nullable=False),
        sa.Column('device_model', sa.String(length=128), nullable=False),
        sa.Column('os_platform', sa.String(length=32), nullable=False),
        sa.Column('os_version', sa.String(length=32), nullable=False),
        sa.Column('app_version', sa.String(length=32), nullable=False),
        sa.Column('app_build_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('is_trusted', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_blocked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('block_reason', sa.Text(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_ip_address', sa.String(length=64), nullable=True),
        sa.Column('device_metadata', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'device_fingerprint', name='uq_student_device_fingerprint'),
    )
    op.create_index(op.f('ix_device_registrations_student_id'), 'device_registrations', ['student_id'], unique=False)
    op.create_index(op.f('ix_device_registrations_device_fingerprint'), 'device_registrations', ['device_fingerprint'], unique=False)

    # 3. Create mobile_exam_sessions table
    op.create_table(
        'mobile_exam_sessions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('device_id', sa.Uuid(), nullable=True),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('secure_mode_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('kiosk_mode_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('app_state', sa.String(length=32), server_default=sa.text("'foreground'"), nullable=False),
        sa.Column('last_foreground_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_background_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interruption_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('recovery_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('integrity_status', sa.String(length=32), server_default=sa.text("'verified'"), nullable=False),
        sa.Column('root_detected', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('session_metadata', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['device_registrations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id'),
    )
    op.create_index(op.f('ix_mobile_exam_sessions_attempt_id'), 'mobile_exam_sessions', ['attempt_id'], unique=True)
    op.create_index(op.f('ix_mobile_exam_sessions_device_id'), 'mobile_exam_sessions', ['device_id'], unique=False)
    op.create_index(op.f('ix_mobile_exam_sessions_student_id'), 'mobile_exam_sessions', ['student_id'], unique=False)
    op.create_index(op.f('ix_mobile_exam_sessions_quiz_id'), 'mobile_exam_sessions', ['quiz_id'], unique=False)

    # 4. Create mobile_interruption_events table
    op.create_table(
        'mobile_interruption_events',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('mobile_session_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('interruption_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), server_default=sa.text("'LOW'"), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('details', json_type, nullable=True),
        sa.Column('client_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('server_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mobile_session_id'], ['mobile_exam_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mobile_interruption_events_mobile_session_id'), 'mobile_interruption_events', ['mobile_session_id'], unique=False)
    op.create_index(op.f('ix_mobile_interruption_events_attempt_id'), 'mobile_interruption_events', ['attempt_id'], unique=False)


def downgrade():
    op.drop_table('mobile_interruption_events')
    op.drop_table('mobile_exam_sessions')
    op.drop_table('device_registrations')

    op.drop_column('quiz_configurations', 'block_rooted_devices')
    op.drop_column('quiz_configurations', 'allow_device_recovery')
    op.drop_column('quiz_configurations', 'mobile_interruption_policy')
    op.drop_column('quiz_configurations', 'min_ios_version')
    op.drop_column('quiz_configurations', 'min_android_version')
    op.drop_column('quiz_configurations', 'require_kiosk_mode')
    op.drop_column('quiz_configurations', 'ios_secure_mode')
    op.drop_column('quiz_configurations', 'android_secure_mode')
    op.drop_column('quiz_configurations', 'require_native_app')
