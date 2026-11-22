"""screenshot_screen_recording_watermark_phase23

Revision ID: 0012_screenshot_screen_recording_watermark_phase23
Revises: 0011_advanced_browser_examination_lockdown
Create Date: 2026-11-22 07:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0012_screenshot_screen_recording_watermark_phase23'
down_revision = '0011_advanced_browser_examination_lockdown'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB, 'postgresql')

    # 1. Add Phase 23 columns to quiz_configurations
    op.add_column('quiz_configurations', sa.Column('watermark_opacity', sa.Numeric(precision=3, scale=2), server_default=sa.text('0.06'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_font_size', sa.Integer(), server_default=sa.text('12'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_rotation_deg', sa.Integer(), server_default=sa.text('-25'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_spacing_px', sa.Integer(), server_default=sa.text('140'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_update_interval_sec', sa.Integer(), server_default=sa.text('30'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_mask_student_id', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_show_timestamp', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_show_exam_id', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('watermark_custom_text', sa.String(length=255), nullable=True))
    op.add_column('quiz_configurations', sa.Column('require_watermark_validation', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('block_screen_capture_api', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('track_screenshot_signals', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('quiz_configurations', sa.Column('track_screen_recording_signals', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    # 2. Add Phase 23 columns to examination_security_policies
    op.add_column('examination_security_policies', sa.Column('watermark_opacity', sa.Numeric(precision=3, scale=2), server_default=sa.text('0.06'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_font_size', sa.Integer(), server_default=sa.text('12'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_rotation_deg', sa.Integer(), server_default=sa.text('-25'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_spacing_px', sa.Integer(), server_default=sa.text('140'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_update_interval_sec', sa.Integer(), server_default=sa.text('30'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_mask_student_id', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_show_timestamp', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_show_exam_id', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('watermark_custom_text', sa.String(length=255), nullable=True))
    op.add_column('examination_security_policies', sa.Column('require_watermark_validation', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('block_screen_capture_api', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('track_screenshot_signals', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('examination_security_policies', sa.Column('track_screen_recording_signals', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    # 3. Create watermark_sessions table
    op.create_table(
        'watermark_sessions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('watermark_code', sa.String(length=32), nullable=False),
        sa.Column('watermark_text', sa.String(length=512), nullable=False),
        sa.Column('student_display_name', sa.String(length=255), nullable=False),
        sa.Column('student_masked_identifier', sa.String(length=128), nullable=False),
        sa.Column('institution_name', sa.String(length=255), server_default=sa.text("'QUIZVERSE'"), nullable=False),
        sa.Column('opacity', sa.Numeric(precision=3, scale=2), server_default=sa.text('0.06'), nullable=False),
        sa.Column('font_size', sa.Integer(), server_default=sa.text('12'), nullable=False),
        sa.Column('rotation_deg', sa.Integer(), server_default=sa.text('-25'), nullable=False),
        sa.Column('spacing_px', sa.Integer(), server_default=sa.text('140'), nullable=False),
        sa.Column('update_interval_sec', sa.Integer(), server_default=sa.text('30'), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('verification_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_valid', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('tamper_flag', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('metadata_json', json_type, nullable=True),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', name='uq_watermark_session_attempt'),
        sa.UniqueConstraint('watermark_code', name='uq_watermark_session_code')
    )
    op.create_index(op.f('ix_watermark_sessions_attempt_id'), 'watermark_sessions', ['attempt_id'], unique=True)
    op.create_index(op.f('ix_watermark_sessions_quiz_id'), 'watermark_sessions', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_watermark_sessions_student_id'), 'watermark_sessions', ['student_id'], unique=False)
    op.create_index(op.f('ix_watermark_sessions_watermark_code'), 'watermark_sessions', ['watermark_code'], unique=True)

    # 4. Create capture_capability_reports table
    op.create_table(
        'capture_capability_reports',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('attempt_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('student_id', sa.Uuid(), nullable=False),
        sa.Column('screen_capture_api_supported', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('screenshot_shortcut_supported', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('display_media_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('detection_tier', sa.String(length=32), server_default=sa.text("'detection_limited'"), nullable=False),
        sa.Column('browser_vendor', sa.String(length=64), server_default=sa.text("'Unknown'"), nullable=False),
        sa.Column('os_platform', sa.String(length=64), server_default=sa.text("'Unknown'"), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['examination_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capture_capability_reports_attempt_id'), 'capture_capability_reports', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_capture_capability_reports_quiz_id'), 'capture_capability_reports', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_capture_capability_reports_student_id'), 'capture_capability_reports', ['student_id'], unique=False)


def downgrade():
    op.drop_table('capture_capability_reports')
    op.drop_table('watermark_sessions')

    # Drop columns from examination_security_policies
    op.drop_column('examination_security_policies', 'track_screen_recording_signals')
    op.drop_column('examination_security_policies', 'track_screenshot_signals')
    op.drop_column('examination_security_policies', 'block_screen_capture_api')
    op.drop_column('examination_security_policies', 'require_watermark_validation')
    op.drop_column('examination_security_policies', 'watermark_custom_text')
    op.drop_column('examination_security_policies', 'watermark_show_exam_id')
    op.drop_column('examination_security_policies', 'watermark_show_timestamp')
    op.drop_column('examination_security_policies', 'watermark_mask_student_id')
    op.drop_column('examination_security_policies', 'watermark_update_interval_sec')
    op.drop_column('examination_security_policies', 'watermark_spacing_px')
    op.drop_column('examination_security_policies', 'watermark_rotation_deg')
    op.drop_column('examination_security_policies', 'watermark_font_size')
    op.drop_column('examination_security_policies', 'watermark_opacity')

    # Drop columns from quiz_configurations
    op.drop_column('quiz_configurations', 'track_screen_recording_signals')
    op.drop_column('quiz_configurations', 'track_screenshot_signals')
    op.drop_column('quiz_configurations', 'block_screen_capture_api')
    op.drop_column('quiz_configurations', 'require_watermark_validation')
    op.drop_column('quiz_configurations', 'watermark_custom_text')
    op.drop_column('quiz_configurations', 'watermark_show_exam_id')
    op.drop_column('quiz_configurations', 'watermark_show_timestamp')
    op.drop_column('quiz_configurations', 'watermark_mask_student_id')
    op.drop_column('quiz_configurations', 'watermark_update_interval_sec')
    op.drop_column('quiz_configurations', 'watermark_spacing_px')
    op.drop_column('quiz_configurations', 'watermark_rotation_deg')
    op.drop_column('quiz_configurations', 'watermark_font_size')
    op.drop_column('quiz_configurations', 'watermark_opacity')
