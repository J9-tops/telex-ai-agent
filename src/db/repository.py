from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from src.models.job import Job, Skill, TrendAnalysis, SkillTrend
from src.schemas.job import JobSearchQuery, TrendQuery


class JobRepository:
    """Repository for job-related database operations"""

    @staticmethod
    def create_job(db: Session, job_data: Dict[str, Any]) -> Job:
        """Create a new job entry"""
        job = Job(**job_data)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def bulk_create_jobs(db: Session, jobs_data: List[Dict[str, Any]]) -> int:
        """Bulk insert jobs"""
        jobs = [Job(**job_data) for job_data in jobs_data]
        db.bulk_save_objects(jobs)
        db.commit()
        return len(jobs)

    @staticmethod
    def get_job_by_id(db: Session, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return db.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def get_job_by_slug(db: Session, slug: str) -> Optional[Job]:
        """Get job by slug"""
        return db.query(Job).filter(Job.slug == slug).first()

    @staticmethod
    def search_jobs(db: Session, query: JobSearchQuery) -> List[Job]:
        """Search jobs with filters"""
        q = db.query(Job)

        if query.company:
            q = q.filter(Job.company.ilike(f"%{query.company}%"))

        if query.location:
            q = q.filter(Job.location.ilike(f"%{query.location}%"))

        if query.remote_only:
            q = q.filter(Job.remote_allowed == True)

        if query.min_salary:
            q = q.filter(Job.salary_min >= query.min_salary)

        if query.date_from:
            q = q.filter(Job.date_posted >= query.date_from)

        if query.skills:
            for skill in query.skills:
                q = q.filter(Job.tags.contains([skill]))

        q = q.order_by(desc(Job.date_posted))
        q = q.offset(query.offset).limit(query.limit)

        return q.all()

    @staticmethod
    def get_recent_jobs(db: Session, days: int = 7, limit: int = 100) -> List[Job]:
        """Get recent jobs within specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(Job)
            .filter(Job.date_posted >= cutoff_date)
            .order_by(desc(Job.date_posted))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_total_jobs(db: Session) -> int:
        """Get total number of jobs"""
        return db.query(func.count(Job.id)).scalar()

    @staticmethod
    def get_jobs_count_by_period(db: Session, hours: int = 24) -> int:
        """Get count of jobs posted in last N hours"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            db.query(func.count(Job.id)).filter(Job.date_posted >= cutoff_date).scalar()
        )


class SkillRepository:
    """Repository for skill-related database operations"""

    @staticmethod
    def create_or_update_skill(
        db: Session, name: str, category: str = "general"
    ) -> Skill:
        """Create new skill or update existing one"""
        normalized = name.lower().strip()
        skill = db.query(Skill).filter(Skill.normalized_name == normalized).first()

        if skill:
            skill.last_seen = datetime.now(timezone.utc)
            skill.total_mentions += 1
        else:
            skill = Skill(
                name=name,
                normalized_name=normalized,
                category=category,
                total_mentions=1,
            )
            db.add(skill)

        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def get_all_skills(db: Session, limit: int = 1000) -> List[Skill]:
        """Get all skills"""
        return db.query(Skill).order_by(desc(Skill.total_mentions)).limit(limit).all()

    @staticmethod
    def get_top_skills(db: Session, limit: int = 50) -> List[Skill]:
        """Get top skills by mentions"""
        return db.query(Skill).order_by(desc(Skill.total_mentions)).limit(limit).all()

    @staticmethod
    def get_skills_by_category(db: Session, category: str) -> List[Skill]:
        """Get skills filtered by category"""
        return (
            db.query(Skill)
            .filter(Skill.category == category)
            .order_by(desc(Skill.total_mentions))
            .all()
        )


class TrendRepository:
    """Repository for trend analysis operations"""

    @staticmethod
    def create_trend_analysis(
        db: Session, analysis_data: Dict[str, Any]
    ) -> TrendAnalysis:
        """Create new trend analysis"""
        analysis = TrendAnalysis(**analysis_data)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def get_latest_analysis(db: Session) -> Optional[TrendAnalysis]:
        """Get the most recent trend analysis"""
        return (
            db.query(TrendAnalysis).order_by(desc(TrendAnalysis.analysis_date)).first()
        )

    @staticmethod
    def get_analyses_by_period(
        db: Session, days: int = 30, limit: int = 10
    ) -> List[TrendAnalysis]:
        """Get trend analyses from last N days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(TrendAnalysis)
            .filter(TrendAnalysis.analysis_date >= cutoff_date)
            .order_by(desc(TrendAnalysis.analysis_date))
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_skill_trend(db: Session, trend_data: Dict[str, Any]) -> SkillTrend:
        """Create skill trend entry"""
        trend = SkillTrend(**trend_data)
        db.add(trend)
        db.commit()
        db.refresh(trend)
        return trend

    @staticmethod
    def get_skill_trends(
        db: Session, skill_name: str, days: int = 30
    ) -> List[SkillTrend]:
        """Get trend data for a specific skill"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(SkillTrend)
            .filter(
                and_(
                    SkillTrend.skill_name == skill_name, SkillTrend.date >= cutoff_date
                )
            )
            .order_by(SkillTrend.date)
            .all()
        )
