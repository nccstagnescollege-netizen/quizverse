"""RBAC, admin scopes, and session management

Revision ID: 0003_rbac_and_admin_scopes
Revises: 0002_complete_database_schema
Create Date: 2026-11-17 19:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_rbac_and_admin_scopes'
down_revision: Union[str, None] = '0002_complete_database_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_super_admin, password_hash, and last_login_at to admins table
    op.add_column(
        'admins',
        sa.Column('is_super_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )
    op.add_column(
        'admins',
        sa.Column('password_hash', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'admins',
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 2. admin_quiz_assignments
    op.create_table(
        'admin_quiz_assignments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('quiz_id', sa.Uuid(), nullable=False),
        sa.Column('access_level', sa.String(length=32), server_default=sa.text("'editor'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admin_id', 'quiz_id', name='uq_admin_quiz_assignment')
    )
    op.create_index('ix_admin_quiz_assignments_admin_id', 'admin_quiz_assignments', ['admin_id'])
    op.create_index('ix_admin_quiz_assignments_quiz_id', 'admin_quiz_assignments', ['quiz_id'])

    # 3. admin_academic_scope
    op.create_table(
        'admin_academic_scope',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('unit_id', sa.Uuid(), nullable=True),
        sa.Column('topic_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_academic_scope_admin_id', 'admin_academic_scope', ['admin_id'])
    op.create_index('ix_admin_academic_scope_unit_id', 'admin_academic_scope', ['unit_id'])
    op.create_index('ix_admin_academic_scope_topic_id', 'admin_academic_scope', ['topic_id'])

    # 4. admin_permission_overrides
    op.create_table(
        'admin_permission_overrides',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('permission_id', sa.Uuid(), nullable=False),
        sa.Column('is_granted', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admin_id', 'permission_id', name='uq_admin_perm_override')
    )
    op.create_index('ix_admin_permission_overrides_admin_id', 'admin_permission_overrides', ['admin_id'])
    op.create_index('ix_admin_permission_overrides_permission_id', 'admin_permission_overrides', ['permission_id'])

    # 5. admin_sessions
    op.create_table(
        'admin_sessions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=False),
        sa.Column('token_jti', sa.String(length=128), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_jti', name='uq_admin_sessions_token_jti')
    )
    op.create_index('ix_admin_sessions_admin_id', 'admin_sessions', ['admin_id'])
    op.create_index('ix_admin_sessions_token_jti', 'admin_sessions', ['token_jti'])

    # Seed core roles and permissions
    roles_table = sa.table(
        'roles',
        sa.column('id', sa.Uuid),
        sa.column('role_name', sa.String),
        sa.column('description', sa.Text),
    )

    super_admin_role_id = uuid.uuid4()
    user_admin_role_id = uuid.uuid4()

    op.bulk_insert(
        roles_table,
        [
            {
                'id': super_admin_role_id,
                'role_name': 'super_admin',
                'description': 'Unrestricted root administrator with complete platform governance',
            },
            {
                'id': user_admin_role_id,
                'role_name': 'user_admin',
                'description': 'Operational administrator with scoped quiz, bank, and candidate permissions',
            },
        ]
    )

    # Core granular permissions
    permissions_table = sa.table(
        'permissions',
        sa.column('id', sa.Uuid),
        sa.column('permission_name', sa.String),
        sa.column('description', sa.Text),
    )

    permission_definitions = [
        # Quizzes
        ('quiz.view', 'View permitted examination records'),
        ('quiz.create', 'Create new examination records'),
        ('quiz.edit', 'Edit permitted examination records'),
        ('quiz.delete', 'Delete permitted examination records'),
        ('quiz.publish', 'Publish or unpublish examinations'),
        ('quiz.schedule', 'Configure start and end exam windows'),
        ('quiz.export', 'Export quiz definition and metadata'),
        # Questions
        ('question.view', 'View question bank entries'),
        ('question.create', 'Author new question bank entries'),
        ('question.edit', 'Edit question bank entries and options'),
        ('question.delete', 'Delete or archive questions'),
        ('question.import', 'Bulk import questions from CSV/JSON'),
        ('question.export', 'Bulk export questions'),
        # Academic
        ('academic.view', 'View units, chapters, and topics'),
        ('academic.create', 'Create units, chapters, and topics'),
        ('academic.edit', 'Edit units, chapters, and topics'),
        ('academic.delete', 'Archive academic units and topics'),
        # Students & Registration
        ('student.view', 'View student registrations and profiles'),
        ('student.export', 'Export student rosters and details'),
        ('registration.manage', 'Configure custom registration forms'),
        # Results & Analytics
        ('results.view', 'View examination submissions and marks'),
        ('results.export', 'Export candidate grade reports'),
        ('analytics.view', 'Access psychometric item analysis and metrics'),
        ('examination.monitor', 'Access real-time examination telemetry and alerts'),
        # Super Admin only
        ('admin.manage', 'Create, edit, disable, and manage administrator accounts'),
        ('permissions.manage', 'Assign and revoke administrative roles and permissions'),
        ('settings.manage', 'Configure system-wide settings and security policies'),
        ('audit_logs.view', 'Inspect immutable administrative audit logs'),
    ]

    seeded_perms = []
    user_admin_perm_ids = []

    for key, desc in permission_definitions:
        perm_id = uuid.uuid4()
        seeded_perms.append({
            'id': perm_id,
            'permission_name': key,
            'description': desc,
        })
        if not key.startswith(('admin.', 'permissions.', 'settings.', 'audit_logs.')):
            user_admin_perm_ids.append(perm_id)

    op.bulk_insert(permissions_table, seeded_perms)

    # Bind permissions to user_admin role
    role_perms_table = sa.table(
        'role_permissions',
        sa.column('role_id', sa.Uuid),
        sa.column('permission_id', sa.Uuid),
    )

    role_perms_data = [
        {
            'role_id': user_admin_role_id,
            'permission_id': p_id,
        }
        for p_id in user_admin_perm_ids
    ]
    op.bulk_insert(role_perms_table, role_perms_data)

    # Enable RLS on new tables if on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        for tbl in ['admin_quiz_assignments', 'admin_academic_scope', 'admin_permission_overrides', 'admin_sessions']:
            op.execute(sa.text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY"))


def downgrade() -> None:
    op.drop_table('admin_sessions')
    op.drop_table('admin_permission_overrides')
    op.drop_table('admin_academic_scope')
    op.drop_table('admin_quiz_assignments')
    op.drop_column('admins', 'last_login_at')
    op.drop_column('admins', 'password_hash')
    op.drop_column('admins', 'is_super_admin')
