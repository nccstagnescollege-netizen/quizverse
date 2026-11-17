import uuid
from sqlalchemy import Column, String, Text, DateTime, Uuid, ForeignKey, func, text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    auth_user_id = Column(Uuid, unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    admin_roles = relationship("AdminRole", back_populates="admin", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="admin_roles", back_populates="admins", viewonly=True)
    created_questions = relationship("Question", back_populates="creator")
    created_quizzes = relationship("Quiz", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="admin")


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
