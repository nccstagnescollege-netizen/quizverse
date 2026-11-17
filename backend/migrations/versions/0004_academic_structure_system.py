"""Academic structure management system

Revision ID: 0004_academic_structure_system
Revises: 0003_rbac_and_admin_scopes
Create Date: 2026-11-17 20:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_academic_structure_system'
down_revision: Union[str, None] = '0003_rbac_and_admin_scopes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. institutions table
    op.create_table(
        'institutions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=512), nullable=True),
        sa.Column('website_url', sa.String(length=512), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_institutions_code')
    )
    op.create_index('ix_institutions_code', 'institutions', ['code'])

    # 2. programmes table
    op.create_table(
        'programmes',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('institution_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('degree_type', sa.String(length=64), server_default=sa.text("'Undergraduate'"), nullable=False),
        sa.Column('duration_years', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('total_semesters', sa.Integer(), server_default=sa.text('6'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('institution_id', 'code', name='uq_programme_institution_code')
    )
    op.create_index('ix_programmes_institution_id', 'programmes', ['institution_id'])
    op.create_index('ix_programmes_code', 'programmes', ['code'])

    # 3. academic_sessions table
    op.create_table(
        'academic_sessions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('institution_id', sa.Uuid(), nullable=True),
        sa.Column('session_name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_academic_sessions_institution_id', 'academic_sessions', ['institution_id'])

    # 4. programme_years table
    op.create_table(
        'programme_years',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('programme_id', sa.Uuid(), nullable=False),
        sa.Column('year_number', sa.Integer(), nullable=False),
        sa.Column('year_name', sa.String(length=100), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('programme_id', 'year_number', name='uq_programme_year_num')
    )
    op.create_index('ix_programme_years_programme_id', 'programme_years', ['programme_id'])

    # 5. semesters table
    op.create_table(
        'semesters',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('programme_id', sa.Uuid(), nullable=False),
        sa.Column('programme_year_id', sa.Uuid(), nullable=True),
        sa.Column('semester_number', sa.Integer(), nullable=False),
        sa.Column('semester_name', sa.String(length=100), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['programme_year_id'], ['programme_years.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('programme_id', 'semester_number', name='uq_programme_semester_num')
    )
    op.create_index('ix_semesters_programme_id', 'semesters', ['programme_id'])
    op.create_index('ix_semesters_programme_year_id', 'semesters', ['programme_year_id'])

    # 6. subject_categories table
    op.create_table(
        'subject_categories',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=False),
        sa.Column('category_code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_name', name='uq_subject_categories_name'),
        sa.UniqueConstraint('category_code', name='uq_subject_categories_code')
    )

    # 7. subjects table
    op.create_table(
        'subjects',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('institution_id', sa.Uuid(), nullable=True),
        sa.Column('subject_name', sa.String(length=255), nullable=False),
        sa.Column('subject_code', sa.String(length=64), nullable=False),
        sa.Column('subject_type', sa.String(length=64), server_default=sa.text("'theory'"), nullable=False),
        sa.Column('default_credits', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('syllabus_version', sa.String(length=32), server_default=sa.text("'1.0'"), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subject_code', name='uq_subjects_code')
    )
    op.create_index('ix_subjects_institution_id', 'subjects', ['institution_id'])
    op.create_index('ix_subjects_subject_code', 'subjects', ['subject_code'])

    # 8. curricula table
    op.create_table(
        'curricula',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('programme_id', sa.Uuid(), nullable=False),
        sa.Column('academic_session_id', sa.Uuid(), nullable=True),
        sa.Column('curriculum_name', sa.String(length=255), nullable=False),
        sa.Column('version_code', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['academic_session_id'], ['academic_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('programme_id', 'version_code', name='uq_curriculum_programme_version')
    )
    op.create_index('ix_curricula_programme_id', 'curricula', ['programme_id'])
    op.create_index('ix_curricula_academic_session_id', 'curricula', ['academic_session_id'])

    # 9. curriculum_subjects table
    op.create_table(
        'curriculum_subjects',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('curriculum_id', sa.Uuid(), nullable=False),
        sa.Column('semester_id', sa.Uuid(), nullable=False),
        sa.Column('subject_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=True),
        sa.Column('credits', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('is_elective', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('elective_group', sa.String(length=64), nullable=True),
        sa.Column('syllabus_version', sa.String(length=32), server_default=sa.text("'1.0'"), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['subject_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['curriculum_id'], ['curricula.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('curriculum_id', 'semester_id', 'subject_id', name='uq_curriculum_sem_subject')
    )
    op.create_index('ix_curriculum_subjects_curriculum_id', 'curriculum_subjects', ['curriculum_id'])
    op.create_index('ix_curriculum_subjects_semester_id', 'curriculum_subjects', ['semester_id'])
    op.create_index('ix_curriculum_subjects_subject_id', 'curriculum_subjects', ['subject_id'])
    op.create_index('ix_curriculum_subjects_category_id', 'curriculum_subjects', ['category_id'])

    # 10. Add subject_id & unit_number to units
    op.add_column('units', sa.Column('subject_id', sa.Uuid(), nullable=True))
    op.add_column('units', sa.Column('unit_number', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_foreign_key('fk_units_subject_id', 'units', 'subjects', ['subject_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_units_subject_id', 'units', ['subject_id'])

    # 11. Add chapter_number to chapters
    op.add_column('chapters', sa.Column('chapter_number', sa.Integer(), server_default=sa.text('1'), nullable=False))

    # 12. Add topic_code to topics
    op.add_column('topics', sa.Column('topic_code', sa.String(length=64), nullable=True))

    # 13. Add academic scoping columns to admin_academic_scope
    op.add_column('admin_academic_scope', sa.Column('institution_id', sa.Uuid(), nullable=True))
    op.add_column('admin_academic_scope', sa.Column('programme_id', sa.Uuid(), nullable=True))
    op.add_column('admin_academic_scope', sa.Column('curriculum_id', sa.Uuid(), nullable=True))
    op.add_column('admin_academic_scope', sa.Column('subject_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_admin_scope_institution', 'admin_academic_scope', 'institutions', ['institution_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_admin_scope_programme', 'admin_academic_scope', 'programmes', ['programme_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_admin_scope_curriculum', 'admin_academic_scope', 'curricula', ['curriculum_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_admin_scope_subject', 'admin_academic_scope', 'subjects', ['subject_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_admin_academic_scope_institution_id', 'admin_academic_scope', ['institution_id'])
    op.create_index('ix_admin_academic_scope_programme_id', 'admin_academic_scope', ['programme_id'])
    op.create_index('ix_admin_academic_scope_curriculum_id', 'admin_academic_scope', ['curriculum_id'])
    op.create_index('ix_admin_academic_scope_subject_id', 'admin_academic_scope', ['subject_id'])

    # 14. Seed standard subject categories
    categories = [
        ('Major', 'MAJOR', 'Discipline-specific primary core subject required for programme completion'),
        ('Minor', 'MINOR', 'Secondary specialization discipline or complementary domain subject'),
        ('Elective', 'ELECTIVE', 'Departmental or open elective choice offered to candidates'),
        ('Generic Elective', 'GEN_ELEC', 'Interdisciplinary elective open across different faculties'),
        ('Skill Enhancement', 'SEC', 'Practical, application-oriented skill enhancement course'),
        ('Ability Enhancement', 'AEC', 'Foundational competence course such as Environmental Science or English'),
        ('Language', 'LANG', 'Modern or classical language subject'),
        ('Foundation', 'FOUNDATION', 'Core institutional values and computational foundation subject'),
        ('Common Subject', 'COMMON', 'Multi-programme shared curriculum component'),
    ]
    for name, code, desc in categories:
        op.execute(
            sa.text(
                "INSERT INTO subject_categories (id, category_name, category_code, description, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :name, :code, :desc, NOW(), NOW()) "
                "ON CONFLICT (category_code) DO NOTHING;"
            ).bindparams(name=name, code=code, desc=desc)
        )


def downgrade() -> None:
    # Drop foreign keys and columns on admin_academic_scope
    op.drop_constraint('fk_admin_scope_subject', 'admin_academic_scope', type_='foreignkey')
    op.drop_constraint('fk_admin_scope_curriculum', 'admin_academic_scope', type_='foreignkey')
    op.drop_constraint('fk_admin_scope_programme', 'admin_academic_scope', type_='foreignkey')
    op.drop_constraint('fk_admin_scope_institution', 'admin_academic_scope', type_='foreignkey')
    op.drop_column('admin_academic_scope', 'subject_id')
    op.drop_column('admin_academic_scope', 'curriculum_id')
    op.drop_column('admin_academic_scope', 'programme_id')
    op.drop_column('admin_academic_scope', 'institution_id')

    # Drop columns on topics, chapters, units
    op.drop_column('topics', 'topic_code')
    op.drop_column('chapters', 'chapter_number')
    op.drop_constraint('fk_units_subject_id', 'units', type_='foreignkey')
    op.drop_column('units', 'unit_number')
    op.drop_column('units', 'subject_id')

    # Drop academic hierarchy tables
    op.drop_table('curriculum_subjects')
    op.drop_table('curricula')
    op.drop_table('subjects')
    op.drop_table('subject_categories')
    op.drop_table('semesters')
    op.drop_table('programme_years')
    op.drop_table('academic_sessions')
    op.drop_table('programmes')
    op.drop_table('institutions')
