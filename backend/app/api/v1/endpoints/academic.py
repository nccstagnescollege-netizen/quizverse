import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_, func

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, AdminAcademicScope
from backend.app.models.academic import (
    Institution,
    Programme,
    AcademicSession,
    ProgrammeYear,
    Semester,
    SubjectCategory,
    Subject,
    Curriculum,
    CurriculumSubject,
    Unit,
    Chapter,
    Topic,
)
from backend.app.models.question_bank import Question
from backend.app.schemas.academic import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionResponse,
    ProgrammeCreate,
    ProgrammeUpdate,
    ProgrammeResponse,
    AcademicSessionCreate,
    AcademicSessionUpdate,
    AcademicSessionResponse,
    ProgrammeYearResponse,
    SemesterCreate,
    SemesterResponse,
    SubjectCategoryCreate,
    SubjectCategoryResponse,
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    CurriculumCreate,
    CurriculumResponse,
    CurriculumSubjectAllocate,
    CurriculumSubjectResponse,
    UnitCreate,
    UnitUpdate,
    UnitResponse,
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    AcademicTreeNode,
    ReorderItemsRequest,
    AssignAcademicScopeRequest,
)
from backend.app.services.rbac_service import (
    get_current_admin,
    require_super_admin,
    require_permission,
    require_any_permission,
    check_academic_scope,
    get_admin_academic_scopes,
)
from backend.app.services.audit_service import log_audit_event

router = APIRouter()


# ==============================================================================
# 1. INSTITUTIONS
# ==============================================================================

@router.get("/institutions", response_model=List[InstitutionResponse])
async def list_institutions(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List institutions. Super Admin sees all; User Admin sees institutions in their scope."""
    query = db.query(Institution)
    if status_filter:
        query = query.filter(Institution.status == status_filter)
    else:
        query = query.filter(Institution.status != "archived")

    if not admin.is_super_admin:
        scopes = get_admin_academic_scopes(db, admin)
        if not scopes.get("has_any_scope"):
            return []
        allowed_insts = scopes.get("institutions", set())
        # Also include institutions that own allowed programmes
        allowed_prog_insts = set(
            db.query(Programme.institution_id)
            .filter(Programme.id.in_(scopes.get("programmes", set())))
            .all()
        )
        all_allowed = allowed_insts.union({p[0] for p in allowed_prog_insts})
        query = query.filter(Institution.id.in_(all_allowed))

    institutions = query.order_by(Institution.name).all()
    results = []
    for inst in institutions:
        prog_count = db.query(Programme).filter(Programme.institution_id == inst.id).count()
        subj_count = db.query(Subject).filter(Subject.institution_id == inst.id).count()
        results.append(
            InstitutionResponse(
                id=inst.id,
                name=inst.name,
                code=inst.code,
                description=inst.description,
                logo_url=inst.logo_url,
                website_url=inst.website_url,
                address=inst.address,
                status=inst.status,
                programmes_count=prog_count,
                subjects_count=subj_count,
                created_at=inst.created_at,
                updated_at=inst.updated_at,
            )
        )
    return results


@router.post("/institutions", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a new academic institution."""
    existing = db.query(Institution).filter(Institution.code == payload.code.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution with code '{payload.code}' already exists.",
        )

    inst = Institution(
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        description=payload.description,
        logo_url=payload.logo_url,
        website_url=payload.website_url,
        address=payload.address,
        status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    log_audit_event(
        db,
        action="institution.create",
        entity_name="institutions",
        entity_id=inst.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": inst.name, "code": inst.code},
    )

    return InstitutionResponse(
        id=inst.id,
        name=inst.name,
        code=inst.code,
        description=inst.description,
        logo_url=inst.logo_url,
        website_url=inst.website_url,
        address=inst.address,
        status=inst.status,
        programmes_count=0,
        subjects_count=0,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


@router.get("/institutions/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """Get single institution details."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    if not check_academic_scope(db, admin, institution_id=institution_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    prog_count = db.query(Programme).filter(Programme.institution_id == inst.id).count()
    subj_count = db.query(Subject).filter(Subject.institution_id == inst.id).count()

    return InstitutionResponse(
        id=inst.id,
        name=inst.name,
        code=inst.code,
        description=inst.description,
        logo_url=inst.logo_url,
        website_url=inst.website_url,
        address=inst.address,
        status=inst.status,
        programmes_count=prog_count,
        subjects_count=subj_count,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


@router.put("/institutions/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: uuid.UUID,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update institution details."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    if not check_academic_scope(db, admin, institution_id=institution_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.name is not None:
        inst.name = payload.name.strip()
    if payload.code is not None:
        code_clean = payload.code.strip().upper()
        existing = db.query(Institution).filter(Institution.code == code_clean, Institution.id != institution_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Code '{code_clean}' already taken.")
        inst.code = code_clean
    if payload.description is not None:
        inst.description = payload.description
    if payload.logo_url is not None:
        inst.logo_url = payload.logo_url
    if payload.website_url is not None:
        inst.website_url = payload.website_url
    if payload.address is not None:
        inst.address = payload.address
    if payload.status is not None:
        inst.status = payload.status

    db.commit()
    db.refresh(inst)

    log_audit_event(
        db,
        action="institution.update",
        entity_name="institutions",
        entity_id=inst.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": inst.name, "code": inst.code, "status": inst.status},
    )

    prog_count = db.query(Programme).filter(Programme.institution_id == inst.id).count()
    subj_count = db.query(Subject).filter(Subject.institution_id == inst.id).count()

    return InstitutionResponse(
        id=inst.id,
        name=inst.name,
        code=inst.code,
        description=inst.description,
        logo_url=inst.logo_url,
        website_url=inst.website_url,
        address=inst.address,
        status=inst.status,
        programmes_count=prog_count,
        subjects_count=subj_count,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


@router.delete("/institutions/{institution_id}", status_code=status.HTTP_200_OK)
async def archive_institution(
    institution_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive an institution."""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    if not check_academic_scope(db, admin, institution_id=institution_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    inst.status = "archived"
    db.commit()

    log_audit_event(
        db,
        action="institution.archive",
        entity_name="institutions",
        entity_id=inst.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": inst.name, "code": inst.code},
    )
    return {"success": True, "message": f"Institution '{inst.name}' archived."}


# ==============================================================================
# 2. PROGRAMMES
# ==============================================================================

@router.get("/programmes", response_model=List[ProgrammeResponse])
async def list_programmes(
    institution_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List academic programmes with optional filtering by institution and status."""
    query = db.query(Programme)
    if institution_id:
        query = query.filter(Programme.institution_id == institution_id)
    if status_filter:
        query = query.filter(Programme.status == status_filter)
    else:
        query = query.filter(Programme.status != "archived")

    if not admin.is_super_admin:
        scopes = get_admin_academic_scopes(db, admin)
        if not scopes.get("has_any_scope"):
            return []
        allowed_progs = scopes.get("programmes", set())
        allowed_insts = scopes.get("institutions", set())
        query = query.filter(or_(Programme.id.in_(allowed_progs), Programme.institution_id.in_(allowed_insts)))

    programmes = query.order_by(Programme.name).all()
    results = []
    for p in programmes:
        inst_name = p.institution.name if p.institution else None
        results.append(
            ProgrammeResponse(
                id=p.id,
                institution_id=p.institution_id,
                institution_name=inst_name,
                name=p.name,
                code=p.code,
                degree_type=p.degree_type,
                duration_years=p.duration_years,
                total_semesters=p.total_semesters,
                description=p.description,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return results


@router.post("/programmes", response_model=ProgrammeResponse, status_code=status.HTTP_201_CREATED)
async def create_programme(
    payload: ProgrammeCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """
    Create a new programme.
    Automatically generates ProgrammeYear records (1..duration_years)
    and Semester records (1..total_semesters) distributed cleanly across years.
    """
    if not check_academic_scope(db, admin, institution_id=payload.institution_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    inst = db.query(Institution).filter(Institution.id == payload.institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    code_clean = payload.code.strip().upper()
    existing = db.query(Programme).filter(
        Programme.institution_id == payload.institution_id,
        Programme.code == code_clean,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Programme with code '{code_clean}' already exists in this institution.",
        )

    prog = Programme(
        institution_id=payload.institution_id,
        name=payload.name.strip(),
        code=code_clean,
        degree_type=payload.degree_type,
        duration_years=payload.duration_years,
        total_semesters=payload.total_semesters,
        description=payload.description,
        status="active",
    )
    db.add(prog)
    db.flush()

    # Automatically provision programme years
    years = []
    for y_idx in range(1, payload.duration_years + 1):
        year_obj = ProgrammeYear(
            programme_id=prog.id,
            year_number=y_idx,
            year_name=f"Year {y_idx}",
            display_order=y_idx,
        )
        db.add(year_obj)
        years.append(year_obj)
    db.flush()

    # Provision semesters and map to corresponding years
    sems_per_year = max(1, payload.total_semesters // payload.duration_years)
    for s_idx in range(1, payload.total_semesters + 1):
        assigned_year_idx = min((s_idx - 1) // sems_per_year, len(years) - 1)
        year_id = years[assigned_year_idx].id if years else None
        sem_obj = Semester(
            programme_id=prog.id,
            programme_year_id=year_id,
            semester_number=s_idx,
            semester_name=f"Semester {s_idx}",
            display_order=s_idx,
            status="active",
        )
        db.add(sem_obj)

    db.commit()
    db.refresh(prog)

    log_audit_event(
        db,
        action="programme.create",
        entity_name="programmes",
        entity_id=prog.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": prog.name, "code": prog.code, "total_semesters": prog.total_semesters},
    )

    return ProgrammeResponse(
        id=prog.id,
        institution_id=prog.institution_id,
        institution_name=inst.name,
        name=prog.name,
        code=prog.code,
        degree_type=prog.degree_type,
        duration_years=prog.duration_years,
        total_semesters=prog.total_semesters,
        description=prog.description,
        status=prog.status,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )


@router.get("/programmes/{programme_id}", response_model=ProgrammeResponse)
async def get_programme(
    programme_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """Get single programme details."""
    prog = db.query(Programme).filter(Programme.id == programme_id).first()
    if not prog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")

    if not check_academic_scope(db, admin, programme_id=programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    return ProgrammeResponse(
        id=prog.id,
        institution_id=prog.institution_id,
        institution_name=prog.institution.name if prog.institution else None,
        name=prog.name,
        code=prog.code,
        degree_type=prog.degree_type,
        duration_years=prog.duration_years,
        total_semesters=prog.total_semesters,
        description=prog.description,
        status=prog.status,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )


@router.put("/programmes/{programme_id}", response_model=ProgrammeResponse)
async def update_programme(
    programme_id: uuid.UUID,
    payload: ProgrammeUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update programme metadata."""
    prog = db.query(Programme).filter(Programme.id == programme_id).first()
    if not prog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")

    if not check_academic_scope(db, admin, programme_id=programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.name is not None:
        prog.name = payload.name.strip()
    if payload.code is not None:
        code_clean = payload.code.strip().upper()
        existing = db.query(Programme).filter(
            Programme.institution_id == prog.institution_id,
            Programme.code == code_clean,
            Programme.id != programme_id,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Code '{code_clean}' already taken in this institution.")
        prog.code = code_clean
    if payload.degree_type is not None:
        prog.degree_type = payload.degree_type
    if payload.duration_years is not None:
        prog.duration_years = payload.duration_years
    if payload.total_semesters is not None:
        prog.total_semesters = payload.total_semesters
    if payload.description is not None:
        prog.description = payload.description
    if payload.status is not None:
        prog.status = payload.status

    db.commit()
    db.refresh(prog)

    log_audit_event(
        db,
        action="programme.update",
        entity_name="programmes",
        entity_id=prog.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": prog.name, "code": prog.code, "status": prog.status},
    )

    return ProgrammeResponse(
        id=prog.id,
        institution_id=prog.institution_id,
        institution_name=prog.institution.name if prog.institution else None,
        name=prog.name,
        code=prog.code,
        degree_type=prog.degree_type,
        duration_years=prog.duration_years,
        total_semesters=prog.total_semesters,
        description=prog.description,
        status=prog.status,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )


@router.delete("/programmes/{programme_id}", status_code=status.HTTP_200_OK)
async def archive_programme(
    programme_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive a programme."""
    prog = db.query(Programme).filter(Programme.id == programme_id).first()
    if not prog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")

    if not check_academic_scope(db, admin, programme_id=programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    prog.status = "archived"
    db.commit()

    log_audit_event(
        db,
        action="programme.archive",
        entity_name="programmes",
        entity_id=prog.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": prog.name, "code": prog.code},
    )
    return {"success": True, "message": f"Programme '{prog.name}' archived."}


# ==============================================================================
# 3. ACADEMIC SESSIONS
# ==============================================================================

@router.get("/sessions", response_model=List[AcademicSessionResponse])
async def list_sessions(
    institution_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List academic sessions."""
    query = db.query(AcademicSession)
    if institution_id:
        query = query.filter(or_(AcademicSession.institution_id == institution_id, AcademicSession.institution_id.is_(None)))
    sessions = query.order_by(desc(AcademicSession.is_current), desc(AcademicSession.session_name)).all()
    return sessions


@router.post("/sessions", response_model=AcademicSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: AcademicSessionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create an academic session. If marked is_current, resets previous current sessions."""
    if payload.is_current and payload.institution_id:
        db.query(AcademicSession).filter(AcademicSession.institution_id == payload.institution_id).update({"is_current": False})

    session_obj = AcademicSession(
        session_name=payload.session_name.strip(),
        institution_id=payload.institution_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        status="active",
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


# ==============================================================================
# 4. PROGRAMME YEARS & SEMESTERS
# ==============================================================================

@router.get("/programmes/{programme_id}/semesters", response_model=List[SemesterResponse])
async def list_semesters(
    programme_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List all semesters belonging to a programme."""
    if not check_academic_scope(db, admin, programme_id=programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    semesters = (
        db.query(Semester)
        .filter(Semester.programme_id == programme_id)
        .order_by(Semester.semester_number)
        .all()
    )
    return semesters


@router.post("/semesters", response_model=SemesterResponse, status_code=status.HTTP_201_CREATED)
async def create_semester(
    payload: SemesterCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create an additional semester for a programme."""
    if not check_academic_scope(db, admin, programme_id=payload.programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    existing = db.query(Semester).filter(
        Semester.programme_id == payload.programme_id,
        Semester.semester_number == payload.semester_number,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Semester number {payload.semester_number} already exists.")

    sem = Semester(
        programme_id=payload.programme_id,
        programme_year_id=payload.programme_year_id,
        semester_number=payload.semester_number,
        semester_name=payload.semester_name.strip(),
        display_order=payload.display_order,
        status="active",
    )
    db.add(sem)
    db.commit()
    db.refresh(sem)
    return sem


# ==============================================================================
# 5. SUBJECT CATEGORIES
# ==============================================================================

@router.get("/categories", response_model=List[SubjectCategoryResponse])
async def list_subject_categories(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List all standard and custom subject categories."""
    return db.query(SubjectCategory).order_by(SubjectCategory.category_name).all()


@router.post("/categories", response_model=SubjectCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_subject_category(
    payload: SubjectCategoryCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a new custom subject category."""
    code_clean = payload.category_code.strip().upper()
    existing = db.query(SubjectCategory).filter(
        or_(
            SubjectCategory.category_code == code_clean,
            SubjectCategory.category_name == payload.category_name.strip(),
        )
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject category already exists.")

    cat = SubjectCategory(
        category_name=payload.category_name.strip(),
        category_code=code_clean,
        description=payload.description,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ==============================================================================
# 6. SUBJECTS (REUSABLE MASTER SUBJECTS)
# ==============================================================================

@router.get("/subjects", response_model=List[SubjectResponse])
async def list_subjects(
    institution_id: Optional[uuid.UUID] = None,
    subject_type: Optional[str] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """
    List reusable master subjects.
    Super Admin sees all; User Admin is restricted to subjects in their assigned academic scopes.
    """
    query = db.query(Subject)
    if institution_id:
        query = query.filter(or_(Subject.institution_id == institution_id, Subject.institution_id.is_(None)))
    if subject_type:
        query = query.filter(Subject.subject_type == subject_type)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(or_(Subject.subject_name.ilike(search_fmt), Subject.subject_code.ilike(search_fmt)))
    if status_filter:
        query = query.filter(Subject.status == status_filter)
    else:
        query = query.filter(Subject.status != "archived")

    if not admin.is_super_admin:
        scopes = get_admin_academic_scopes(db, admin)
        if not scopes.get("has_any_scope"):
            return []
        allowed_subjs = scopes.get("subjects", set())
        allowed_progs = scopes.get("programmes", set())
        allowed_currs = scopes.get("curricula", set())
        allowed_insts = scopes.get("institutions", set())

        # Also find subjects allocated to allowed programmes or curricula
        allocated_subquery = (
            db.query(CurriculumSubject.subject_id)
            .join(Curriculum, Curriculum.id == CurriculumSubject.curriculum_id)
            .filter(
                or_(
                    CurriculumSubject.curriculum_id.in_(allowed_currs) if allowed_currs else False,
                    Curriculum.programme_id.in_(allowed_progs) if allowed_progs else False,
                )
            )
            .all()
        )
        allocated_subj_ids = {s[0] for s in allocated_subquery}
        all_allowed_subjs = allowed_subjs.union(allocated_subj_ids)

        query = query.filter(
            or_(
                Subject.id.in_(all_allowed_subjs),
                Subject.institution_id.in_(allowed_insts) if allowed_insts else False,
            )
        )

    subjects = query.order_by(Subject.subject_code).all()
    results = []
    for s in subjects:
        u_count = db.query(Unit).filter(Unit.subject_id == s.id).count()
        results.append(
            SubjectResponse(
                id=s.id,
                institution_id=s.institution_id,
                subject_name=s.subject_name,
                subject_code=s.subject_code,
                subject_type=s.subject_type,
                default_credits=s.default_credits,
                description=s.description,
                syllabus_version=s.syllabus_version,
                status=s.status,
                units_count=u_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return results


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a new reusable master subject."""
    code_clean = payload.subject_code.strip().upper()
    existing = db.query(Subject).filter(Subject.subject_code == code_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject with code '{code_clean}' already exists.",
        )

    if payload.institution_id and not check_academic_scope(db, admin, institution_id=payload.institution_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    subj = Subject(
        institution_id=payload.institution_id,
        subject_name=payload.subject_name.strip(),
        subject_code=code_clean,
        subject_type=payload.subject_type,
        default_credits=payload.default_credits,
        description=payload.description,
        syllabus_version=payload.syllabus_version,
        status="active",
    )
    db.add(subj)
    db.commit()
    db.refresh(subj)

    log_audit_event(
        db,
        action="subject.create",
        entity_name="subjects",
        entity_id=subj.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": subj.subject_name, "code": subj.subject_code},
    )

    return SubjectResponse(
        id=subj.id,
        institution_id=subj.institution_id,
        subject_name=subj.subject_name,
        subject_code=subj.subject_code,
        subject_type=subj.subject_type,
        default_credits=subj.default_credits,
        description=subj.description,
        syllabus_version=subj.syllabus_version,
        status=subj.status,
        units_count=0,
        created_at=subj.created_at,
        updated_at=subj.updated_at,
    )


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """Get single subject details."""
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if not check_academic_scope(db, admin, subject_id=subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    u_count = db.query(Unit).filter(Unit.subject_id == subj.id).count()
    return SubjectResponse(
        id=subj.id,
        institution_id=subj.institution_id,
        subject_name=subj.subject_name,
        subject_code=subj.subject_code,
        subject_type=subj.subject_type,
        default_credits=subj.default_credits,
        description=subj.description,
        syllabus_version=subj.syllabus_version,
        status=subj.status,
        units_count=u_count,
        created_at=subj.created_at,
        updated_at=subj.updated_at,
    )


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update subject properties."""
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if not check_academic_scope(db, admin, subject_id=subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.subject_name is not None:
        subj.subject_name = payload.subject_name.strip()
    if payload.subject_code is not None:
        code_clean = payload.subject_code.strip().upper()
        existing = db.query(Subject).filter(Subject.subject_code == code_clean, Subject.id != subject_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Code '{code_clean}' already taken.")
        subj.subject_code = code_clean
    if payload.subject_type is not None:
        subj.subject_type = payload.subject_type
    if payload.default_credits is not None:
        subj.default_credits = payload.default_credits
    if payload.description is not None:
        subj.description = payload.description
    if payload.syllabus_version is not None:
        subj.syllabus_version = payload.syllabus_version
    if payload.status is not None:
        subj.status = payload.status

    db.commit()
    db.refresh(subj)

    log_audit_event(
        db,
        action="subject.update",
        entity_name="subjects",
        entity_id=subj.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": subj.subject_name, "code": subj.subject_code, "status": subj.status},
    )

    u_count = db.query(Unit).filter(Unit.subject_id == subj.id).count()
    return SubjectResponse(
        id=subj.id,
        institution_id=subj.institution_id,
        subject_name=subj.subject_name,
        subject_code=subj.subject_code,
        subject_type=subj.subject_type,
        default_credits=subj.default_credits,
        description=subj.description,
        syllabus_version=subj.syllabus_version,
        status=subj.status,
        units_count=u_count,
        created_at=subj.created_at,
        updated_at=subj.updated_at,
    )


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_200_OK)
async def archive_subject(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive a subject."""
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if not check_academic_scope(db, admin, subject_id=subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    subj.status = "archived"
    db.commit()

    log_audit_event(
        db,
        action="subject.archive",
        entity_name="subjects",
        entity_id=subj.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": subj.subject_name, "code": subj.subject_code},
    )
    return {"success": True, "message": f"Subject '{subj.subject_name}' archived."}


# ==============================================================================
# 7. CURRICULA & ALLOCATION
# ==============================================================================

@router.get("/curricula", response_model=List[CurriculumResponse])
async def list_curricula(
    programme_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List curricula."""
    query = db.query(Curriculum)
    if programme_id:
        query = query.filter(Curriculum.programme_id == programme_id)

    if not admin.is_super_admin:
        scopes = get_admin_academic_scopes(db, admin)
        if not scopes.get("has_any_scope"):
            return []
        allowed_currs = scopes.get("curricula", set())
        allowed_progs = scopes.get("programmes", set())
        query = query.filter(or_(Curriculum.id.in_(allowed_currs), Curriculum.programme_id.in_(allowed_progs)))

    curricula = query.order_by(desc(Curriculum.is_active), Curriculum.curriculum_name).all()
    results = []
    for c in curricula:
        alloc_count = db.query(CurriculumSubject).filter(CurriculumSubject.curriculum_id == c.id).count()
        results.append(
            CurriculumResponse(
                id=c.id,
                programme_id=c.programme_id,
                academic_session_id=c.academic_session_id,
                curriculum_name=c.curriculum_name,
                version_code=c.version_code,
                is_active=c.is_active,
                description=c.description,
                status=c.status,
                allocated_subjects_count=alloc_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return results


@router.post("/curricula", response_model=CurriculumResponse, status_code=status.HTTP_201_CREATED)
async def create_curriculum(
    payload: CurriculumCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a new curriculum version for a programme."""
    if not check_academic_scope(db, admin, programme_id=payload.programme_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    version_clean = payload.version_code.strip().upper()
    existing = db.query(Curriculum).filter(
        Curriculum.programme_id == payload.programme_id,
        Curriculum.version_code == version_clean,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Curriculum version '{version_clean}' already exists for this programme.",
        )

    curr = Curriculum(
        programme_id=payload.programme_id,
        academic_session_id=payload.academic_session_id,
        curriculum_name=payload.curriculum_name.strip(),
        version_code=version_clean,
        is_active=True,
        description=payload.description,
        status="active",
    )
    db.add(curr)
    db.commit()
    db.refresh(curr)

    log_audit_event(
        db,
        action="curriculum.create",
        entity_name="curricula",
        entity_id=curr.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": curr.curriculum_name, "version": curr.version_code},
    )

    return CurriculumResponse(
        id=curr.id,
        programme_id=curr.programme_id,
        academic_session_id=curr.academic_session_id,
        curriculum_name=curr.curriculum_name,
        version_code=curr.version_code,
        is_active=curr.is_active,
        description=curr.description,
        status=curr.status,
        allocated_subjects_count=0,
        created_at=curr.created_at,
        updated_at=curr.updated_at,
    )


@router.get("/curricula/{curriculum_id}/allocations", response_model=List[CurriculumSubjectResponse])
async def list_curriculum_allocations(
    curriculum_id: uuid.UUID,
    semester_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List all subjects allocated within a curriculum, optionally filtered by semester."""
    if not check_academic_scope(db, admin, curriculum_id=curriculum_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    query = db.query(CurriculumSubject).filter(CurriculumSubject.curriculum_id == curriculum_id)
    if semester_id:
        query = query.filter(CurriculumSubject.semester_id == semester_id)

    allocations = query.order_by(CurriculumSubject.display_order).all()
    results = []
    for a in allocations:
        results.append(
            CurriculumSubjectResponse(
                id=a.id,
                curriculum_id=a.curriculum_id,
                semester_id=a.semester_id,
                subject_id=a.subject_id,
                category_id=a.category_id,
                credits=a.credits,
                is_elective=a.is_elective,
                elective_group=a.elective_group,
                syllabus_version=a.syllabus_version,
                display_order=a.display_order,
                status=a.status,
                subject_name=a.subject.subject_name if a.subject else None,
                subject_code=a.subject.subject_code if a.subject else None,
                category_name=a.category.category_name if a.category else None,
            )
        )
    return results


@router.post("/curricula/allocate", response_model=CurriculumSubjectResponse, status_code=status.HTTP_201_CREATED)
async def allocate_subject_to_curriculum(
    payload: CurriculumSubjectAllocate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """
    Allocate a master subject to a curriculum semester.
    Supports defining category (Major, Minor, Elective, Language, etc.),
    custom credits, and elective flags.
    Enforces reusability across multiple programmes!
    """
    if not check_academic_scope(db, admin, curriculum_id=payload.curriculum_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    curr = db.query(Curriculum).filter(Curriculum.id == payload.curriculum_id).first()
    if not curr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

    sem = db.query(Semester).filter(Semester.id == payload.semester_id).first()
    if not sem or sem.programme_id != curr.programme_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Semester does not belong to this curriculum's programme.")

    subj = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not subj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    existing = db.query(CurriculumSubject).filter(
        CurriculumSubject.curriculum_id == payload.curriculum_id,
        CurriculumSubject.semester_id == payload.semester_id,
        CurriculumSubject.subject_id == payload.subject_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject '{subj.subject_code}' is already allocated to this semester in this curriculum.",
        )

    alloc = CurriculumSubject(
        curriculum_id=payload.curriculum_id,
        semester_id=payload.semester_id,
        subject_id=payload.subject_id,
        category_id=payload.category_id,
        credits=payload.credits,
        is_elective=payload.is_elective,
        elective_group=payload.elective_group,
        syllabus_version=payload.syllabus_version,
        display_order=payload.display_order,
        status="active",
    )
    db.add(alloc)
    db.commit()
    db.refresh(alloc)

    log_audit_event(
        db,
        action="curriculum.allocate_subject",
        entity_name="curriculum_subjects",
        entity_id=alloc.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={
            "curriculum_id": str(payload.curriculum_id),
            "semester_id": str(payload.semester_id),
            "subject_code": subj.subject_code,
            "credits": payload.credits,
        },
    )

    return CurriculumSubjectResponse(
        id=alloc.id,
        curriculum_id=alloc.curriculum_id,
        semester_id=alloc.semester_id,
        subject_id=alloc.subject_id,
        category_id=alloc.category_id,
        credits=alloc.credits,
        is_elective=alloc.is_elective,
        elective_group=alloc.elective_group,
        syllabus_version=alloc.syllabus_version,
        display_order=alloc.display_order,
        status=alloc.status,
        subject_name=subj.subject_name,
        subject_code=subj.subject_code,
        category_name=alloc.category.category_name if alloc.category else None,
    )


@router.delete("/curricula/allocate/{allocation_id}", status_code=status.HTTP_200_OK)
async def remove_subject_allocation(
    allocation_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Deallocate a subject from a curriculum semester."""
    alloc = db.query(CurriculumSubject).filter(CurriculumSubject.id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found.")

    if not check_academic_scope(db, admin, curriculum_id=alloc.curriculum_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    db.delete(alloc)
    db.commit()

    log_audit_event(
        db,
        action="curriculum.deallocate_subject",
        entity_name="curriculum_subjects",
        entity_id=allocation_id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"allocation_id": str(allocation_id)},
    )
    return {"success": True, "message": "Subject removed from curriculum semester."}


# ==============================================================================
# 8. UNITS, CHAPTERS & TOPICS (PRESERVING COMPATIBILITY FOR QUESTIONS)
# ==============================================================================

@router.get("/units", response_model=List[UnitResponse])
async def list_units(
    subject_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List units, optionally filtered by subject."""
    query = db.query(Unit)
    if subject_id:
        if not check_academic_scope(db, admin, subject_id=subject_id, strict_for_user_admin=True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")
        query = query.filter(Unit.subject_id == subject_id)
    elif not admin.is_super_admin:
        scopes = get_admin_academic_scopes(db, admin)
        if not scopes.get("has_any_scope"):
            return []
        allowed_units = scopes.get("units", set())
        allowed_subjs = scopes.get("subjects", set())
        query = query.filter(or_(Unit.id.in_(allowed_units), Unit.subject_id.in_(allowed_subjs)))

    units = query.filter(Unit.status != "archived").order_by(Unit.display_order, Unit.unit_number).all()
    results = []
    for u in units:
        c_count = db.query(Chapter).filter(Chapter.unit_id == u.id).count()
        results.append(
            UnitResponse(
                id=u.id,
                subject_id=u.subject_id,
                unit_number=u.unit_number,
                unit_name=u.unit_name,
                unit_code=u.unit_code,
                description=u.description,
                display_order=u.display_order,
                status=u.status,
                chapters_count=c_count,
            )
        )
    return results


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a new syllabus unit."""
    if payload.subject_id and not check_academic_scope(db, admin, subject_id=payload.subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    code_clean = payload.unit_code.strip().upper()
    existing = db.query(Unit).filter(Unit.unit_code == code_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unit with code '{code_clean}' already exists.")

    unit = Unit(
        subject_id=payload.subject_id,
        unit_number=payload.unit_number,
        unit_name=payload.unit_name.strip(),
        unit_code=code_clean,
        description=payload.description,
        display_order=payload.display_order,
        status="active",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    log_audit_event(
        db,
        action="unit.create",
        entity_name="units",
        entity_id=unit.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"name": unit.unit_name, "code": unit.unit_code},
    )

    return UnitResponse(
        id=unit.id,
        subject_id=unit.subject_id,
        unit_number=unit.unit_number,
        unit_name=unit.unit_name,
        unit_code=unit.unit_code,
        description=unit.description,
        display_order=unit.display_order,
        status=unit.status,
        chapters_count=0,
    )


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: uuid.UUID,
    payload: UnitUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update unit details."""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    if not check_academic_scope(db, admin, unit_id=unit_id, subject_id=unit.subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.unit_name is not None:
        unit.unit_name = payload.unit_name.strip()
    if payload.unit_code is not None:
        code_clean = payload.unit_code.strip().upper()
        existing = db.query(Unit).filter(Unit.unit_code == code_clean, Unit.id != unit_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unit code '{code_clean}' already taken.")
        unit.unit_code = code_clean
    if payload.subject_id is not None:
        unit.subject_id = payload.subject_id
    if payload.unit_number is not None:
        unit.unit_number = payload.unit_number
    if payload.description is not None:
        unit.description = payload.description
    if payload.display_order is not None:
        unit.display_order = payload.display_order
    if payload.status is not None:
        unit.status = payload.status

    db.commit()
    db.refresh(unit)

    c_count = db.query(Chapter).filter(Chapter.unit_id == unit.id).count()
    return UnitResponse(
        id=unit.id,
        subject_id=unit.subject_id,
        unit_number=unit.unit_number,
        unit_name=unit.unit_name,
        unit_code=unit.unit_code,
        description=unit.description,
        display_order=unit.display_order,
        status=unit.status,
        chapters_count=c_count,
    )


@router.delete("/units/{unit_id}", status_code=status.HTTP_200_OK)
async def archive_unit(
    unit_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive a unit."""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    if not check_academic_scope(db, admin, unit_id=unit_id, subject_id=unit.subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    unit.status = "archived"
    db.commit()
    return {"success": True, "message": f"Unit '{unit.unit_name}' archived."}


@router.get("/units/{unit_id}/chapters", response_model=List[ChapterResponse])
async def list_chapters(
    unit_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List chapters under a unit."""
    if not check_academic_scope(db, admin, unit_id=unit_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    chapters = (
        db.query(Chapter)
        .filter(Chapter.unit_id == unit_id, Chapter.status != "archived")
        .order_by(Chapter.display_order, Chapter.chapter_number)
        .all()
    )
    results = []
    for c in chapters:
        t_count = db.query(Topic).filter(Topic.chapter_id == c.id).count()
        results.append(
            ChapterResponse(
                id=c.id,
                unit_id=c.unit_id,
                chapter_number=c.chapter_number,
                chapter_name=c.chapter_name,
                chapter_code=c.chapter_code,
                description=c.description,
                display_order=c.display_order,
                status=c.status,
                topics_count=t_count,
            )
        )
    return results


@router.post("/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    payload: ChapterCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a chapter under a unit."""
    unit = db.query(Unit).filter(Unit.id == payload.unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    if not check_academic_scope(db, admin, unit_id=unit.id, subject_id=unit.subject_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    code_clean = payload.chapter_code.strip().upper()
    existing = db.query(Chapter).filter(
        Chapter.unit_id == payload.unit_id,
        Chapter.chapter_code == code_clean,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Chapter code '{code_clean}' already exists in this unit.")

    chap = Chapter(
        unit_id=payload.unit_id,
        chapter_number=payload.chapter_number,
        chapter_name=payload.chapter_name.strip(),
        chapter_code=code_clean,
        description=payload.description,
        display_order=payload.display_order,
        status="active",
    )
    db.add(chap)
    db.commit()
    db.refresh(chap)

    return ChapterResponse(
        id=chap.id,
        unit_id=chap.unit_id,
        chapter_number=chap.chapter_number,
        chapter_name=chap.chapter_name,
        chapter_code=chap.chapter_code,
        description=chap.description,
        display_order=chap.display_order,
        status=chap.status,
        topics_count=0,
    )


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: uuid.UUID,
    payload: ChapterUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update chapter properties."""
    chap = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")

    if not check_academic_scope(db, admin, unit_id=chap.unit_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.chapter_name is not None:
        chap.chapter_name = payload.chapter_name.strip()
    if payload.chapter_code is not None:
        code_clean = payload.chapter_code.strip().upper()
        existing = db.query(Chapter).filter(
            Chapter.unit_id == chap.unit_id,
            Chapter.chapter_code == code_clean,
            Chapter.id != chapter_id,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Chapter code '{code_clean}' already taken.")
        chap.chapter_code = code_clean
    if payload.chapter_number is not None:
        chap.chapter_number = payload.chapter_number
    if payload.description is not None:
        chap.description = payload.description
    if payload.display_order is not None:
        chap.display_order = payload.display_order
    if payload.status is not None:
        chap.status = payload.status

    db.commit()
    db.refresh(chap)

    t_count = db.query(Topic).filter(Topic.chapter_id == chap.id).count()
    return ChapterResponse(
        id=chap.id,
        unit_id=chap.unit_id,
        chapter_number=chap.chapter_number,
        chapter_name=chap.chapter_name,
        chapter_code=chap.chapter_code,
        description=chap.description,
        display_order=chap.display_order,
        status=chap.status,
        topics_count=t_count,
    )


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_200_OK)
async def archive_chapter(
    chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive a chapter."""
    chap = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")

    if not check_academic_scope(db, admin, unit_id=chap.unit_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    chap.status = "archived"
    db.commit()
    return {"success": True, "message": f"Chapter '{chap.chapter_name}' archived."}


@router.get("/chapters/{chapter_id}/topics", response_model=List[TopicResponse])
async def list_topics(
    chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """List topics under a chapter."""
    chap = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")

    if not check_academic_scope(db, admin, unit_id=chap.unit_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    topics = (
        db.query(Topic)
        .filter(Topic.chapter_id == chapter_id, Topic.status != "archived")
        .order_by(Topic.display_order)
        .all()
    )
    return topics


@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    payload: TopicCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.create")),
):
    """Create a topic under a chapter. Directly links to Question Bank via Question.topic_id."""
    chap = db.query(Chapter).filter(Chapter.id == payload.chapter_id).first()
    if not chap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")

    if not check_academic_scope(db, admin, unit_id=chap.unit_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    topic = Topic(
        chapter_id=payload.chapter_id,
        topic_name=payload.topic_name.strip(),
        topic_code=payload.topic_code.strip().upper() if payload.topic_code else None,
        description=payload.description,
        display_order=payload.display_order,
        status="active",
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.put("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: uuid.UUID,
    payload: TopicUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Update topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    if not check_academic_scope(db, admin, topic_id=topic_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    if payload.topic_name is not None:
        topic.topic_name = payload.topic_name.strip()
    if payload.topic_code is not None:
        topic.topic_code = payload.topic_code.strip().upper()
    if payload.description is not None:
        topic.description = payload.description
    if payload.display_order is not None:
        topic.display_order = payload.display_order
    if payload.status is not None:
        topic.status = payload.status

    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_200_OK)
async def archive_topic(
    topic_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_any_permission(["academic.delete", "academic.archive"])),
):
    """Archive a topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    if not check_academic_scope(db, admin, topic_id=topic_id, strict_for_user_admin=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: outside your assigned academic scope.")

    topic.status = "archived"
    db.commit()
    return {"success": True, "message": f"Topic '{topic.topic_name}' archived."}


# ==============================================================================
# 9. REORDERING
# ==============================================================================

@router.post("/reorder", status_code=status.HTTP_200_OK)
async def reorder_academic_items(
    payload: ReorderItemsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.edit")),
):
    """Reorder units, chapters, topics, or curriculum subjects based on ordered ID list."""
    model_map = {
        "units": Unit,
        "chapters": Chapter,
        "topics": Topic,
        "curriculum_subjects": CurriculumSubject,
    }
    target_model = model_map.get(payload.entity_type)
    if not target_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type for reordering.")

    for order_idx, item_id in enumerate(payload.item_ids, start=1):
        db.query(target_model).filter(target_model.id == item_id).update({"display_order": order_idx})
    db.commit()

    return {"success": True, "message": f"Successfully reordered {len(payload.item_ids)} {payload.entity_type}."}


# ==============================================================================
# 10. INTERACTIVE VISUAL HIERARCHY EXPLORER TREE
# ==============================================================================

@router.get("/tree", response_model=List[AcademicTreeNode])
async def get_academic_hierarchy_tree(
    institution_id: Optional[uuid.UUID] = None,
    programme_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("academic.view")),
):
    """
    Returns the comprehensive hierarchical tree structure:
    Institution -> Programme -> Semester -> Subject -> Unit -> Chapter -> Topic (with question counts).
    Strictly scoped according to user admin academic permissions.
    """
    scopes = get_admin_academic_scopes(db, admin)

    inst_query = db.query(Institution).filter(Institution.status != "archived")
    if institution_id:
        inst_query = inst_query.filter(Institution.id == institution_id)
    if not admin.is_super_admin:
        if not scopes.get("has_any_scope"):
            return []
        allowed_insts = scopes.get("institutions", set())
        # Also include institutions containing allowed programmes
        prog_inst_rows = db.query(Programme.institution_id).filter(Programme.id.in_(scopes.get("programmes", set()))).all()
        allowed_insts = allowed_insts.union({r[0] for r in prog_inst_rows})
        inst_query = inst_query.filter(Institution.id.in_(allowed_insts))

    institutions = inst_query.order_by(Institution.name).all()
    tree = []

    for inst in institutions:
        inst_node = AcademicTreeNode(
            id=f"inst_{inst.id}",
            name=inst.name,
            type="institution",
            code=inst.code,
            metadata={"status": inst.status},
            children=[],
        )

        prog_query = db.query(Programme).filter(Programme.institution_id == inst.id, Programme.status != "archived")
        if programme_id:
            prog_query = prog_query.filter(Programme.id == programme_id)
        if not admin.is_super_admin:
            allowed_progs = scopes.get("programmes", set())
            if inst.id not in scopes.get("institutions", set()):
                prog_query = prog_query.filter(Programme.id.in_(allowed_progs))

        programmes = prog_query.order_by(Programme.name).all()

        for prog in programmes:
            prog_node = AcademicTreeNode(
                id=f"prog_{prog.id}",
                name=prog.name,
                type="programme",
                code=prog.code,
                metadata={"degree_type": prog.degree_type, "duration_years": prog.duration_years, "total_semesters": prog.total_semesters},
                children=[],
            )

            semesters = db.query(Semester).filter(Semester.programme_id == prog.id).order_by(Semester.semester_number).all()

            for sem in semesters:
                sem_node = AcademicTreeNode(
                    id=f"sem_{sem.id}",
                    name=sem.semester_name,
                    type="semester",
                    code=f"SEM-{sem.semester_number}",
                    metadata={"semester_number": sem.semester_number},
                    children=[],
                )

                # Get subjects allocated via active curriculum
                allocations = (
                    db.query(CurriculumSubject)
                    .join(Curriculum, Curriculum.id == CurriculumSubject.curriculum_id)
                    .filter(
                        CurriculumSubject.semester_id == sem.id,
                        Curriculum.is_active == True,
                    )
                    .order_by(CurriculumSubject.display_order)
                    .all()
                )

                for alloc in allocations:
                    subj = alloc.subject
                    if not subj or subj.status == "archived":
                        continue

                    cat_name = alloc.category.category_name if alloc.category else "Core"
                    subj_node = AcademicTreeNode(
                        id=f"subj_{subj.id}_{sem.id}",
                        name=subj.subject_name,
                        type="subject",
                        code=subj.subject_code,
                        metadata={
                            "credits": alloc.credits,
                            "category": cat_name,
                            "is_elective": alloc.is_elective,
                            "subject_type": subj.subject_type,
                        },
                        children=[],
                    )

                    units = db.query(Unit).filter(Unit.subject_id == subj.id, Unit.status != "archived").order_by(Unit.display_order).all()
                    for u in units:
                        unit_node = AcademicTreeNode(
                            id=f"unit_{u.id}",
                            name=u.unit_name,
                            type="unit",
                            code=u.unit_code,
                            metadata={"unit_number": u.unit_number},
                            children=[],
                        )

                        chapters = db.query(Chapter).filter(Chapter.unit_id == u.id, Chapter.status != "archived").order_by(Chapter.display_order).all()
                        for chap in chapters:
                            chap_node = AcademicTreeNode(
                                id=f"chap_{chap.id}",
                                name=chap.chapter_name,
                                type="chapter",
                                code=chap.chapter_code,
                                metadata={"chapter_number": chap.chapter_number},
                                children=[],
                            )

                            topics = db.query(Topic).filter(Topic.chapter_id == chap.id, Topic.status != "archived").order_by(Topic.display_order).all()
                            for top in topics:
                                q_count = db.query(Question).filter(Question.topic_id == top.id).count()
                                top_node = AcademicTreeNode(
                                    id=f"top_{top.id}",
                                    name=top.topic_name,
                                    type="topic",
                                    code=top.topic_code,
                                    metadata={"questions_count": q_count},
                                    children=[],
                                )
                                chap_node.children.append(top_node)

                            unit_node.children.append(chap_node)
                        subj_node.children.append(unit_node)
                    sem_node.children.append(subj_node)
                prog_node.children.append(sem_node)
            inst_node.children.append(prog_node)
        tree.append(inst_node)

    return tree


# ==============================================================================
# 11. ACADEMIC SCOPE ASSIGNMENT (SUPER ADMIN ONLY)
# ==============================================================================

@router.post("/scopes", status_code=status.HTTP_201_CREATED)
async def assign_academic_scope(
    payload: AssignAcademicScopeRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """Assign an academic scope to an administrator (Super Admin only)."""
    target_admin = db.query(Admin).filter(Admin.id == payload.admin_id).first()
    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target administrator not found.")

    scope = AdminAcademicScope(
        admin_id=payload.admin_id,
        institution_id=payload.institution_id,
        programme_id=payload.programme_id,
        curriculum_id=payload.curriculum_id,
        subject_id=payload.subject_id,
        unit_id=payload.unit_id,
        topic_id=payload.topic_id,
    )
    db.add(scope)
    db.commit()
    db.refresh(scope)

    log_audit_event(
        db,
        action="admin.assign_academic_scope",
        entity_name="admin_academic_scope",
        entity_id=scope.id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={
            "target_admin_email": target_admin.email,
            "institution_id": str(payload.institution_id) if payload.institution_id else None,
            "programme_id": str(payload.programme_id) if payload.programme_id else None,
            "subject_id": str(payload.subject_id) if payload.subject_id else None,
        },
    )

    return {"success": True, "scope_id": scope.id, "message": "Academic scope assigned successfully."}


@router.get("/scopes/{admin_id}")
async def get_admin_scopes(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_permission("admin.manage")),
):
    """Get all assigned academic scopes for an administrator."""
    scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin_id).all()
    results = []
    for s in scopes:
        results.append({
            "id": s.id,
            "admin_id": s.admin_id,
            "institution_id": s.institution_id,
            "institution_name": s.institution.name if s.institution else None,
            "programme_id": s.programme_id,
            "programme_name": s.programme.name if s.programme else None,
            "subject_id": s.subject_id,
            "subject_name": s.subject.subject_name if s.subject else None,
            "unit_id": s.unit_id,
            "unit_name": s.unit.unit_name if s.unit else None,
            "topic_id": s.topic_id,
            "topic_name": s.topic.topic_name if s.topic else None,
            "created_at": s.created_at,
        })
    return results


@router.delete("/scopes/{scope_id}", status_code=status.HTTP_200_OK)
async def revoke_academic_scope(
    scope_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_super_admin),
):
    """Revoke an assigned academic scope (Super Admin only)."""
    scope = db.query(AdminAcademicScope).filter(AdminAcademicScope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope assignment not found.")

    db.delete(scope)
    db.commit()

    log_audit_event(
        db,
        action="admin.revoke_academic_scope",
        entity_name="admin_academic_scope",
        entity_id=scope_id,
        actor_id=admin.id,
        actor_email=admin.email,
        details={"scope_id": str(scope_id)},
    )

    return {"success": True, "message": "Academic scope revoked successfully."}
