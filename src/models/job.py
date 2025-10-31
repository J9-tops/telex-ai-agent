from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Boolean,
    JSON,
    Float,
    Index,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Job(Base):
    """Model for storing freelance job postings"""

    __tablename__ = "jobs"

    id = Column(String(100), primary_key=True)
    slug = Column(String(255), unique=True, index=True)
    company = Column(String(255), index=True)
    company_logo = Column(String(500), nullable=True)
    position = Column(String(255), index=True)
    tags = Column(JSON, nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)

    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)

    date_posted = Column(DateTime, index=True)
    date_scraped = Column(DateTime, default=datetime.utcnow)

    remote_allowed = Column(Boolean, default=True)
    apply_url = Column(String(500), nullable=True)
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_date_company", "date_posted", "company"),
        Index("idx_date_tags", "date_posted"),
    )


class Skill(Base):
    """Model for tracking individual skills/technologies"""

    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True)
    category = Column(String(50), index=True)
    normalized_name = Column(String(100), index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    total_mentions = Column(Integer, default=0)


class TrendAnalysis(Base):
    """Model for storing trend analysis results"""

    __tablename__ = "trend_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_date = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_window_days = Column(Integer, default=30)

    trending_skills = Column(JSON, nullable=True)
    trending_roles = Column(JSON, nullable=True)
    trending_companies = Column(JSON, nullable=True)

    total_jobs_analyzed = Column(Integer)
    unique_skills_found = Column(Integer)
    unique_companies = Column(Integer)

    ai_insights = Column(Text, nullable=True)
    skill_clusters = Column(JSON, nullable=True)

    __table_args__ = (Index("idx_analysis_date", "analysis_date"),)


class SkillTrend(Base):
    """Time-series data for skill popularity"""

    __tablename__ = "skill_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(100), index=True)
    date = Column(DateTime, index=True)
    mention_count = Column(Integer, default=0)
    job_count = Column(Integer, default=0)
    growth_rate = Column(Float, nullable=True)

    __table_args__ = (Index("idx_skill_date", "skill_name", "date"),)
