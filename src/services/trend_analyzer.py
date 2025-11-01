import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.repository import JobRepository, SkillRepository, TrendRepository
from src.db.session import get_db_context
from src.models.job import Job, Skill
from src.schemas.job import TrendingSkill, TrendingRole

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Service for analyzing job trends and patterns"""

    def __init__(self, window_days: int = 30):
        self.window_days = window_days

    def analyze_skill_trends(self, db: Session) -> List[TrendingSkill]:
        """Analyze trending skills based on job postings"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        previous_cutoff = cutoff_date - timedelta(days=self.window_days)

        current_jobs = db.query(Job).filter(Job.date_posted >= cutoff_date).all()

        previous_jobs = (
            db.query(Job)
            .filter(Job.date_posted >= previous_cutoff)
            .filter(Job.date_posted < cutoff_date)
            .all()
        )

        current_skills = Counter()
        previous_skills = Counter()

        for job in current_jobs:
            if job.tags:
                for tag in job.tags:
                    current_skills[tag.lower()] += 1

        for job in previous_jobs:
            if job.tags:
                for tag in job.tags:
                    previous_skills[tag.lower()] += 1

        trending_skills = []
        for skill, current_count in current_skills.most_common(50):
            previous_count = previous_skills.get(skill, 0)

            if previous_count == 0:
                growth_rate = float(current_count) if current_count > 5 else 0.0
            else:
                growth_rate = ((current_count - previous_count) / previous_count) * 100

            trending_skills.append(
                TrendingSkill(
                    skill_name=skill,
                    current_mentions=current_count,
                    previous_mentions=previous_count,
                    growth_rate=round(growth_rate, 2),
                    growth_percentage=f"{growth_rate:+.1f}%",
                )
            )

        trending_skills.sort(key=lambda x: x.growth_rate, reverse=True)

        return trending_skills[:20]

    def analyze_role_trends(self, db: Session) -> List[TrendingRole]:
        """Analyze trending job roles/positions"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.window_days)
        previous_cutoff = cutoff_date - timedelta(days=self.window_days)

        current_jobs = db.query(Job).filter(Job.date_posted >= cutoff_date).all()

        previous_jobs = (
            db.query(Job)
            .filter(Job.date_posted >= previous_cutoff)
            .filter(Job.date_posted < cutoff_date)
            .all()
        )

        current_roles = Counter()
        previous_roles = Counter()
        role_skills = defaultdict(Counter)

        for job in current_jobs:
            role = self._normalize_role(job.position)
            current_roles[role] += 1

            if job.tags:
                for tag in job.tags:
                    role_skills[role][tag.lower()] += 1

        for job in previous_jobs:
            role = self._normalize_role(job.position)
            previous_roles[role] += 1

        trending_roles = []
        for role, current_count in current_roles.most_common(20):
            previous_count = previous_roles.get(role, 0)

            if previous_count == 0:
                growth_rate = float(current_count) if current_count > 3 else 0.0
            else:
                growth_rate = ((current_count - previous_count) / previous_count) * 100

            top_skills = [skill for skill, _ in role_skills[role].most_common(5)]

            trending_roles.append(
                TrendingRole(
                    role_name=role,
                    job_count=current_count,
                    growth_rate=round(growth_rate, 2),
                    top_skills=top_skills,
                )
            )

        trending_roles.sort(key=lambda x: x.job_count, reverse=True)

        return trending_roles[:15]

    def _normalize_role(self, position: str) -> str:
        """Normalize job position titles"""
        if not position:
            return "Other"

        position = position.lower().strip()

        role_keywords = {
            "developer": ["developer", "dev ", "engineer", "programmer"],
            "designer": ["designer", "design"],
            "manager": ["manager", "lead", "head"],
            "data": ["data scientist", "data analyst", "data engineer"],
            "devops": ["devops", "sre", "site reliability"],
            "frontend": ["frontend", "front-end", "front end"],
            "backend": ["backend", "back-end", "back end"],
            "fullstack": ["fullstack", "full-stack", "full stack"],
            "mobile": ["mobile", "ios", "android"],
            "qa": ["qa", "quality assurance", "tester"],
            "product": ["product manager", "product owner"],
            "marketing": ["marketing", "growth", "seo"],
            "sales": ["sales", "account executive"],
        }

        for role, keywords in role_keywords.items():
            for keyword in keywords:
                if keyword in position:
                    return role.title()

        return "Other"

    def identify_skill_clusters(self, db: Session) -> Dict[str, List[str]]:
        """Identify skills that often appear together"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.window_days)

        jobs = db.query(Job).filter(Job.date_posted >= cutoff_date).all()

        skill_pairs = defaultdict(int)

        for job in jobs:
            if not job.tags or len(job.tags) < 2:
                continue

            tags = [tag.lower() for tag in job.tags]

            for i in range(len(tags)):
                for j in range(i + 1, len(tags)):
                    pair = tuple(sorted([tags[i], tags[j]]))
                    skill_pairs[pair] += 1

        clusters = defaultdict(set)
        main_skills = [
            "python",
            "javascript",
            "react",
            "node",
            "aws",
            "docker",
            "kubernetes",
        ]

        for main_skill in main_skills:
            related = []
            for (skill1, skill2), count in skill_pairs.items():
                if count < 5:
                    continue
                if skill1 == main_skill:
                    related.append((skill2, count))
                elif skill2 == main_skill:
                    related.append((skill1, count))

            related.sort(key=lambda x: x[1], reverse=True)
            clusters[main_skill] = [skill for skill, _ in related[:5]]

        return dict(clusters)

    async def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete trend analysis"""
        logger.info("Starting trend analysis...")

        with get_db_context() as db:
            trending_skills = self.analyze_skill_trends(db)
            trending_roles = self.analyze_role_trends(db)
            skill_clusters = self.identify_skill_clusters(db)

            total_jobs = JobRepository.get_total_jobs(db)
            recent_jobs = JobRepository.get_jobs_count_by_period(
                db, hours=24 * self.window_days
            )

            analysis_data = {
                "analysis_window_days": self.window_days,
                "trending_skills": [skill.model_dump() for skill in trending_skills],
                "trending_roles": [role.model_dump() for role in trending_roles],
                "total_jobs_analyzed": recent_jobs,
                "unique_skills_found": len(trending_skills),
                "unique_companies": db.query(
                    func.count(func.distinct(Job.company))
                ).scalar(),
                "skill_clusters": skill_clusters,
            }

            TrendRepository.create_trend_analysis(db, analysis_data)

            logger.info("Trend analysis completed")

            return {
                "success": True,
                "trending_skills_count": len(trending_skills),
                "trending_roles_count": len(trending_roles),
                "total_jobs_analyzed": recent_jobs,
            }
