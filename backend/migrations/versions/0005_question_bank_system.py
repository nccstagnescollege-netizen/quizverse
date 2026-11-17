"""Question bank management system

Revision ID: 0005_question_bank_system
Revises: 0004_academic_structure_system
Create Date: 2026-11-17 21:50:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_question_bank_system'
down_revision: Union[str, None] = '0004_academic_structure_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend questions table with academic classification and review fields
    op.add_column('questions', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('questions', sa.Column('institution_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('subject_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('curriculum_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('semester_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('unit_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('chapter_id', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('approved_by', sa.Uuid(), nullable=True))
    op.add_column('questions', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('questions', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('questions', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('short_answer_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('questions', sa.Column('is_mathematical', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('questions', sa.Column('code_language', sa.String(length=32), nullable=True))

    op.create_foreign_key('fk_questions_institution', 'questions', 'institutions', ['institution_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_questions_subject', 'questions', 'subjects', ['subject_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_questions_curriculum', 'questions', 'curricula', ['curriculum_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_questions_semester', 'questions', 'semesters', ['semester_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_questions_unit', 'questions', 'units', ['unit_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_questions_chapter', 'questions', 'chapters', ['chapter_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_questions_approved_by', 'questions', 'admins', ['approved_by'], ['id'], ondelete='SET NULL')

    op.create_index('ix_questions_institution_id', 'questions', ['institution_id'])
    op.create_index('ix_questions_subject_id', 'questions', ['subject_id'])
    op.create_index('ix_questions_curriculum_id', 'questions', ['curriculum_id'])
    op.create_index('ix_questions_semester_id', 'questions', ['semester_id'])
    op.create_index('ix_questions_unit_id', 'questions', ['unit_id'])
    op.create_index('ix_questions_chapter_id', 'questions', ['chapter_id'])
    op.create_index('ix_questions_created_by', 'questions', ['created_by'])

    # 2. question_attachments table
    op.create_table(
        'question_attachments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_type', sa.String(length=128), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('is_student_visible', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_attachments_question_id', 'question_attachments', ['question_id'])

    # 3. question_reviews table
    op.create_table(
        'question_reviews',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('reviewer_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=False),  # submitted, approved, rejected
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_reviews_question_id', 'question_reviews', ['question_id'])

    # 4. platform_settings table
    op.create_table(
        'platform_settings',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('key')
    )

    # 5. Insert default platform settings
    platform_settings_table = sa.table(
        'platform_settings',
        sa.column('key', sa.String),
        sa.column('value', postgresql.JSONB),
        sa.column('description', sa.Text),
    )
    op.bulk_insert(platform_settings_table, [
        {
            'key': 'question_review_workflow',
            'value': {'require_super_admin_approval': False, 'auto_approve_user_admin': True},
            'description': 'Determines whether User Admin questions require Super Admin approval prior to examination inclusion.',
        }
    ])

    # 6. Seed missing Question Bank granular permissions
    permissions_table = sa.table(
        'permissions',
        sa.column('id', sa.Uuid),
        sa.column('permission_name', sa.String),
        sa.column('description', sa.Text),
    )

    new_permissions = [
        ('question.archive', 'Archive or restore question bank entries'),
        ('question.review', 'Submit questions for review or reject with comments'),
        ('question.approve', 'Approve question bank entries for examination inclusion'),
        ('question.tag.manage', 'Create, update, and delete reusable question tags'),
        ('question.attachment.upload', 'Upload and manage question media and documents'),
        ('question.answer.view', 'View answer keys and official explanations for questions'),
    ]

    new_perm_records = []
    user_admin_perm_ids = []
    for key, desc in new_permissions:
        p_id = uuid.uuid4()
        new_perm_records.append({
            'id': p_id,
            'permission_name': key,
            'description': desc,
        })
        # question.approve is reserved for super admin or review managers by default
        if key != 'question.approve':
            user_admin_perm_ids.append(p_id)

    op.bulk_insert(permissions_table, new_perm_records)

    # Bind new user-admin permissions
    bind = op.get_bind()
    user_admin_role = bind.execute(sa.text("SELECT id FROM roles WHERE role_name = 'user_admin'")).fetchone()
    if user_admin_role and user_admin_perm_ids:
        role_perms_table = sa.table(
            'role_permissions',
            sa.column('role_id', sa.Uuid),
            sa.column('permission_id', sa.Uuid),
        )
        op.bulk_insert(role_perms_table, [
            {'role_id': user_admin_role[0], 'permission_id': p_id}
            for p_id in user_admin_perm_ids
        ])

    # Enable RLS
    if bind.dialect.name == 'postgresql':
        for tbl in ['question_attachments', 'question_reviews', 'platform_settings']:
            op.execute(sa.text(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY"))


def downgrade() -> None:
    op.drop_table('platform_settings')
    op.drop_table('question_reviews')
    op.drop_table('question_attachments')

    op.drop_constraint('fk_questions_approved_by', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_chapter', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_unit', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_semester', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_curriculum', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_subject', 'questions', type_='foreignkey')
    op.drop_constraint('fk_questions_institution', 'questions', type_='foreignkey')

    op.drop_column('questions', 'code_language')
    op.drop_column('questions', 'is_mathematical')
    op.drop_column('questions', 'short_answer_config')
    op.drop_column('questions', 'rejection_reason')
    op.drop_column('questions', 'archived_at')
    op.drop_column('questions', 'approved_at')
    op.drop_column('questions', 'approved_by')
    op.drop_column('questions', 'chapter_id')
    op.drop_column('questions', 'unit_id')
    op.drop_column('questions', 'semester_id')
    op.drop_column('questions', 'curriculum_id')
    op.drop_column('questions', 'subject_id')
    op.drop_column('questions', 'institution_id')
    op.drop_column('questions', 'title')
