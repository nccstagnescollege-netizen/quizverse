import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(512), nullable=True)
    website_url = Column(String(512), nullable=True)
    address = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    programmes = relationship("Programme", back_populates="institution", cascade="all, delete-orphan", order_by="Programme.name")
    academic_sessions = relationship("AcademicSession", back_populates="institution", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="institution")


class Programme(Base):
    __tablename__ = "programmes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=False, index=True)
    degree_type = Column(String(64), nullable=False, default="Undergraduate")  # Undergraduate, Postgraduate, Diploma, Doctoral
    duration_years = Column(Integer, nullable=False, default=3)
    total_semesters = Column(Integer, nullable=False, default=6)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_programme_institution_code"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="programmes")
    programme_years = relationship("ProgrammeYear", back_populates="programme", cascade="all, delete-orphan", order_by="ProgrammeYear.year_number")
    semesters = relationship("Semester", back_populates="programme", cascade="all, delete-orphan", order_by="Semester.semester_number")
    curricula = relationship("Curriculum", back_populates="programme", cascade="all, delete-orphan")


class AcademicSession(Base):
    __tablename__ = "academic_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    session_name = Column(String(100), nullable=False)  # e.g., "2026-2027"
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    institution = relationship("Institution", back_populates="academic_sessions")
    curricula = relationship("Curriculum", back_populates="academic_session")


class ProgrammeYear(Base):
    __tablename__ = "programme_years"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    programme_id = Column(Uuid, ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    year_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    year_name = Column(String(100), nullable=False)  # e.g., "Year I", "First Year"
    display_order = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("programme_id", "year_number", name="uq_programme_year_num"),
    )

    # Relationships
    programme = relationship("Programme", back_populates="programme_years")
    semesters = relationship("Semester", back_populates="programme_year")


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    programme_id = Column(Uuid, ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_year_id = Column(Uuid, ForeignKey("programme_years.id", ondelete="SET NULL"), nullable=True, index=True)
    semester_number = Column(Integer, nullable=False)  # 1, 2, 3...
    semester_name = Column(String(100), nullable=False)  # e.g. "Semester I"
    display_order = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("programme_id", "semester_number", name="uq_programme_semester_num"),
    )

    # Relationships
    programme = relationship("Programme", back_populates="semesters")
    programme_year = relationship("ProgrammeYear", back_populates="semesters")
    curriculum_subjects = relationship("CurriculumSubject", back_populates="semester", cascade="all, delete-orphan")


class SubjectCategory(Base):
    __tablename__ = "subject_categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    category_name = Column(String(100), unique=True, nullable=False)  # Major, Minor, Elective, Generic Elective, Skill Enhancement, Ability Enhancement, Language, Foundation, Common Subject
    category_code = Column(String(50), unique=True, nullable=False)  # MAJOR, MINOR, ELECTIVE, GEN_ELEC, SEC, AEC, LANG, FOUNDATION, COMMON
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    curriculum_subjects = relationship("CurriculumSubject", back_populates="category")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    institution_id = Column(Uuid, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_name = Column(String(255), nullable=False)
    subject_code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. CS101, PY301
    subject_type = Column(String(64), nullable=False, default="theory")  # theory, practical, integrated, project
    default_credits = Column(Integer, nullable=False, default=3)
    description = Column(Text, nullable=True)
    syllabus_version = Column(String(32), nullable=False, default="1.0")
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    institution = relationship("Institution", back_populates="subjects")
    units = relationship("Unit", back_populates="subject", cascade="all, delete-orphan", order_by="Unit.display_order")
    curriculum_subjects = relationship("CurriculumSubject", back_populates="subject", cascade="all, delete-orphan")


class Curriculum(Base):
    __tablename__ = "curricula"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    programme_id = Column(Uuid, ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_session_id = Column(Uuid, ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    curriculum_name = Column(String(255), nullable=False)
    version_code = Column(String(64), nullable=False)  # e.g., "V2026.1"
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("programme_id", "version_code", name="uq_curriculum_programme_version"),
    )

    # Relationships
    programme = relationship("Programme", back_populates="curricula")
    academic_session = relationship("AcademicSession", back_populates="curricula")
    curriculum_subjects = relationship("CurriculumSubject", back_populates="curriculum", cascade="all, delete-orphan")


class CurriculumSubject(Base):
    __tablename__ = "curriculum_subjects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    curriculum_id = Column(Uuid, ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True)
    semester_id = Column(Uuid, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Uuid, ForeignKey("subject_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    credits = Column(Integer, nullable=False, default=3)
    is_elective = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    elective_group = Column(String(64), nullable=True)  # e.g. "Elective I", "Open Elective A"
    syllabus_version = Column(String(32), nullable=False, default="1.0")
    display_order = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("curriculum_id", "semester_id", "subject_id", name="uq_curriculum_sem_subject"),
    )

    # Relationships
    curriculum = relationship("Curriculum", back_populates="curriculum_subjects")
    semester = relationship("Semester", back_populates="curriculum_subjects")
    subject = relationship("Subject", back_populates="curriculum_subjects")
    category = relationship("SubjectCategory", back_populates="curriculum_subjects")


class Unit(Base):
    __tablename__ = "units"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    subject_id = Column(Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    unit_number = Column(Integer, nullable=False, default=1)
    unit_name = Column(String(255), nullable=False)
    unit_code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="units")
    chapters = relationship("Chapter", back_populates="unit", cascade="all, delete-orphan", order_by="Chapter.display_order")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    unit_id = Column(Uuid, ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False, default=1)
    chapter_name = Column(String(255), nullable=False)
    chapter_code = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("unit_id", "chapter_code", name="uq_chapters_unit_code"),
    )

    # Relationships
    unit = relationship("Unit", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", cascade="all, delete-orphan", order_by="Topic.display_order")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    chapter_id = Column(Uuid, ForeignKey("chapters.id", ondelete="RESTRICT"), nullable=False, index=True)
    topic_name = Column(String(255), nullable=False)
    topic_code = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    chapter = relationship("Chapter", back_populates="topics")
    questions = relationship("Question", back_populates="topic")
