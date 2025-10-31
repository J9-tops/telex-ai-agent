from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.db.session import get_db
from src.db.repository import JobRepository
from src.schemas.job import JobSchema, JobSearchQuery, StatsResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/", response_model=List[JobSchema])
async def get_jobs(
    company: Optional[str] = Query(None, description="Filter by company name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    remote_only: Optional[bool] = Query(None, description="Show only remote jobs"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get jobs with optional filters"""
    search_query = JobSearchQuery(
        company=company,
        location=location,
        remote_only=remote_only,
        limit=limit,
        offset=offset,
    )

    jobs = JobRepository.search_jobs(db, search_query)
    return jobs


@router.get("/{job_id}", response_model=JobSchema)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job by ID"""
    job = JobRepository.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/recent/list", response_model=List[JobSchema])
async def get_recent_jobs(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """Get recent jobs within specified days"""
    jobs = JobRepository.get_recent_jobs(db, days=days, limit=limit)
    return jobs


@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get overall job statistics"""
    from src.db.repository import SkillRepository

    total_jobs = JobRepository.get_total_jobs(db)
    jobs_24h = JobRepository.get_jobs_count_by_period(db, hours=24)
    jobs_7d = JobRepository.get_jobs_count_by_period(db, hours=24 * 7)

    from sqlalchemy import func
    from src.models.job import Job

    company_stats = (
        db.query(Job.company, func.count(Job.id).label("count"))
        .group_by(Job.company)
        .order_by(func.count(Job.id).desc())
        .first()
    )

    most_active_company = company_stats[0] if company_stats else None

    top_skill = SkillRepository.get_top_skills(db, limit=1)
    most_demanded_skill = top_skill[0].name if top_skill else None

    return StatsResponse(
        total_jobs=total_jobs,
        total_skills=len(SkillRepository.get_all_skills(db, limit=10000)),
        total_companies=db.query(func.count(func.distinct(Job.company))).scalar(),
        jobs_last_24h=jobs_24h,
        jobs_last_7d=jobs_7d,
        most_active_company=most_active_company,
        most_demanded_skill=most_demanded_skill,
    )
