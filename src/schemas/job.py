from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class JobSchema(BaseModel):
    """Schema for job response"""

    id: str
    slug: str
    company: str
    position: str
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    date_posted: datetime
    remote_allowed: bool = True

    model_config = ConfigDict(from_attributes=True)


class SkillSchema(BaseModel):
    """Schema for skill response"""

    name: str
    category: str
    total_mentions: int
    first_seen: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class TrendingSkill(BaseModel):
    """Schema for trending skill data"""

    skill_name: str
    current_mentions: int
    previous_mentions: int
    growth_rate: float
    growth_percentage: str


class TrendingRole(BaseModel):
    """Schema for trending role data"""

    role_name: str
    job_count: int
    growth_rate: float
    top_skills: List[str]


class TrendAnalysisSchema(BaseModel):
    """Schema for trend analysis response"""

    analysis_date: datetime
    analysis_window_days: int
    trending_skills: List[TrendingSkill]
    trending_roles: List[TrendingRole]
    total_jobs_analyzed: int
    unique_skills_found: int
    ai_insights: Optional[str] = None
    skill_clusters: Optional[Dict[str, List[str]]] = None

    model_config = ConfigDict(from_attributes=True)


class JobSearchQuery(BaseModel):
    """Schema for job search parameters"""

    skills: Optional[List[str]] = Field(None, description="Filter by required skills")
    company: Optional[str] = Field(None, description="Filter by company name")
    location: Optional[str] = Field(None, description="Filter by location")
    remote_only: Optional[bool] = Field(None, description="Show only remote jobs")
    min_salary: Optional[int] = Field(None, description="Minimum salary")
    date_from: Optional[datetime] = Field(
        None, description="Jobs posted after this date"
    )
    limit: int = Field(50, ge=1, le=500, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class TrendQuery(BaseModel):
    """Schema for trend analysis query"""

    window_days: int = Field(30, ge=7, le=365, description="Analysis window in days")
    top_n: int = Field(10, ge=1, le=50, description="Number of top items to return")
    category: Optional[str] = Field(None, description="Filter by skill category")


class StatsResponse(BaseModel):
    """Schema for general statistics"""

    total_jobs: int
    total_skills: int
    total_companies: int
    jobs_last_24h: int
    jobs_last_7d: int
    most_active_company: Optional[str] = None
    most_demanded_skill: Optional[str] = None
