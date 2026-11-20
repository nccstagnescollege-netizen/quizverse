import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditFindingItem(BaseModel):
    id: uuid.UUID
    finding_code: str
    category: str
    severity: str
    affected_module: str
    title: str
    description: str
    reproduction_steps: Optional[str] = None
    evidence: Optional[str] = None
    root_cause: Optional[str] = None
    recommended_remediation: Optional[str] = None
    remediation_status: str
    remediation_notes: Optional[str] = None
    retested_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FindingCreateRequest(BaseModel):
    finding_code: str
    category: str
    severity: str = "MEDIUM"
    affected_module: str
    title: str
    description: str
    reproduction_steps: Optional[str] = None
    evidence: Optional[str] = None
    root_cause: Optional[str] = None
    recommended_remediation: Optional[str] = None
    remediation_status: str = "RESOLVED"
    remediation_notes: Optional[str] = None


class FindingUpdateRequest(BaseModel):
    severity: Optional[str] = None
    remediation_status: Optional[str] = None
    remediation_notes: Optional[str] = None


class LoadTestBenchmarkItem(BaseModel):
    id: uuid.UUID
    scenario_name: str
    virtual_users: int
    duration_seconds: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_avg_ms: float
    error_rate_pct: float
    concurrency_target_met: bool
    bottleneck_identified: Optional[str] = None
    environment: str
    created_at: datetime

    class Config:
        from_attributes = True


class AccessibilityCheckpointItem(BaseModel):
    id: uuid.UUID
    checkpoint_code: str
    checkpoint_name: str
    wcag_level: str
    category: str
    compliance_status: str
    automated_score: int
    manual_verification_notes: Optional[str] = None
    tested_components: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosticsCheckItem(BaseModel):
    component: str
    status: str  # PASS, WARNING, FAIL
    latency_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None


class AuditDashboardSummaryResponse(BaseModel):
    release_readiness: str  # READY_FOR_PRODUCTION_REVIEW, READY_FOR_CONTROLLED_PILOT, READY_AFTER_FIXES, NOT_READY
    overall_score: int
    total_findings: int
    severity_counts: Dict[str, int]
    category_counts: Dict[str, int]
    modules_verified_count: int
    total_modules: int
    regression_test_summary: Dict[str, Any]
    load_benchmarks: List[LoadTestBenchmarkItem]
    accessibility_summary: Dict[str, Any]
    disaster_recovery_status: Dict[str, Any]
    cross_browser_compatibility: Dict[str, Any]
    diagnostics: List[DiagnosticsCheckItem]
    findings: List[AuditFindingItem]
