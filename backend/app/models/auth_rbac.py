import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Uuid,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    auth_user_id = Column(Uuid, unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))  # active, disabled, suspended
    is_super_admin = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    admin_roles = relationship("AdminRole", back_populates="admin", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="admin_roles", back_populates="admins", viewonly=True)
    created_questions = relationship("Question", back_populates="creator")
    created_quizzes = relationship("Quiz", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="admin")
    sessions = relationship("AdminSession", back_populates="admin", cascade="all, delete-orphan")
    quiz_assignments = relationship("AdminQuizAssignment", back_populates="admin", cascade="all, delete-orphan")
    academic_scopes = relationship("AdminAcademicScope", back_populates="admin", cascade="all, delete-orphan")
    permission_overrides = relationship("AdminPermissionOverride", back_populates="admin", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    role_name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    admin_roles = relationship("AdminRole", back_populates="role", cascade="all, delete-orphan")
    admins = relationship("Admin", secondary="admin_roles", back_populates="roles", viewonly=True)
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles", viewonly=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    permission_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions", viewonly=True)


class AdminRole(Base):
    __tablename__ = "admin_roles"

    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="admin_roles")
    role = relationship("Role", back_populates="admin_roles")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class AdminQuizAssignment(Base):
    __tablename__ = "admin_quiz_assignments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    access_level = Column(String(32), nullable=False, default="editor", server_default=text("'editor'"))  # owner, editor, viewer
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("admin_id", "quiz_id", name="uq_admin_quiz_assignment"),
    )

    # Relationships
    admin = relationship("Admin", back_populates="quiz_assignments")
    quiz = relationship("Quiz")


class AdminAcademicScope(Base):
    __tablename__ = "admin_academic_scope"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(Uuid, ForeignKey("units.id", ondelete="CASCADE"), nullable=True, index=True)
    topic_id = Column(Uuid, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="academic_scopes")
    unit = relationship("Unit")
    topic = relationship("Topic")


class AdminPermissionOverride(Base):
    __tablename__ = "admin_permission_overrides"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_granted = Column(Boolean, nullable=False, default=True)  # True = grant, False = explicit revoke
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("admin_id", "permission_id", name="uq_admin_perm_override"),
    )

    # Relationships
    admin = relationship("Admin", back_populates="permission_overrides")
    permission = relationship("Permission")


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    admin_id = Column(Uuid, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(128), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())

    # Relationships
    admin = relationship("Admin", back_populates="sessions")
