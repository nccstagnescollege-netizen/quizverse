import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    Uuid,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import utc_now, JSONType


class AuditTestRun(Base):
    """
    Tracks automated quality assurance and test execution runs.
    """
    __tablename__ = "audit_test_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    run_type = Column(String(64), nullable=False, default="FULL_REGRESSION")  # SECURITY, PERFORMANCE, ACCESSIBILITY, FULL_REGRESSION
    runner = Column(String(64), nullable=False, default="SYSTEM_AUDITOR")  # CLI, SYSTEM_AUDITOR, CI_CD
    status = Column(String(32), nullable=False, default="COMPLETED")  # RUNNING, COMPLETED, FAILED
    total_tests = Column(Integer, nullable=False, default=0)
    passed_tests = Column(Integer, nullable=False, default=0)
    failed_tests = Column(Integer, nullable=False, default=0)
    skipped_tests = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Numeric(8, 2), nullable=False, default=0.0)
    details = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())


class AuditFinding(Base):
    """
    Centralized defect and security vulnerability tracker.
    Classifies findings according to OWASP, WCAG, and institutional quality baselines.
    """
    __tablename__ = "audit_findings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    finding_code = Column(String(64), unique=True, nullable=False, index=True)  # e.g. SEC-AUTH-001, PERF-DB-002
    category = Column(String(64), nullable=False, index=True)  # SECURITY, PERFORMANCE, DATA_INTEGRITY, ACCESSIBILITY, RELIABILITY
    severity = Column(String(32), nullable=False, default="MEDIUM", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    affected_module = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reproduction_steps = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    recommended_remediation = Column(Text, nullable=True)
    remediation_status = Column(String(32), nullable=False, default="RESOLVED", index=True)  # RESOLVED, IN_PROGRESS, ACCEPTED_RISK, REOPENED
    remediation_notes = Column(Text, nullable=True)
    verified_by = Column(Uuid, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    retested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())

    # Relationships
    verifier = relationship("Admin", foreign_keys=[verified_by])


class LoadTestBenchmark(Base):
    """
    Records realistic simulated load, concurrency tests, and latency distributions.
    """
    __tablename__ = "load_test_benchmarks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    scenario_name = Column(String(128), nullable=False)  # e.g. "CONCURRENT_EXAMINATION_LOBBY_AND_SUBMIT"
    virtual_users = Column(Integer, nullable=False)  # 10, 25, 50, 100
    duration_seconds = Column(Integer, nullable=False, default=30)
    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    failed_requests = Column(Integer, nullable=False, default=0)
    requests_per_second = Column(Numeric(8, 2), nullable=False, default=0.0)
    latency_p50_ms = Column(Numeric(8, 2), nullable=False, default=0.0)
    latency_p95_ms = Column(Numeric(8, 2), nullable=False, default=0.0)
    latency_p99_ms = Column(Numeric(8, 2), nullable=False, default=0.0)
    latency_avg_ms = Column(Numeric(8, 2), nullable=False, default=0.0)
    error_rate_pct = Column(Numeric(5, 2), nullable=False, default=0.0)
    concurrency_target_met = Column(Boolean, nullable=False, default=True)
    bottleneck_identified = Column(String(255), nullable=True)
    environment = Column(String(64), nullable=False, default="STAGE_TEST")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())


class AccessibilityAuditRecord(Base):
    """
    Tracks accessibility compliance against WCAG 2.2 Level AA.
    """
    __tablename__ = "accessibility_audit_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    checkpoint_code = Column(String(32), unique=True, nullable=False)  # e.g. "WCAG-1.1.1", "WCAG-2.1.1"
    checkpoint_name = Column(String(255), nullable=False)
    wcag_level = Column(String(8), nullable=False, default="AA")  # A, AA, AAA
    category = Column(String(64), nullable=False)  # Perceivable, Operable, Understandable, Robust
    compliance_status = Column(String(32), nullable=False, default="COMPLIANT")  # COMPLIANT, PARTIALLY_COMPLIANT, NON_COMPLIANT
    automated_score = Column(Integer, nullable=False, default=100)  # 0 to 100
    manual_verification_notes = Column(Text, nullable=True)
    tested_components = Column(JSONType, nullable=True)  # List of component names tested
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.now())
