"""Pydantic schemas for request/response validation"""

from src.schemas.job import (
    JobSchema,
    SkillSchema,
    TrendAnalysisSchema,
    TrendingSkill,
    TrendingRole,
    JobSearchQuery,
    TrendQuery,
    StatsResponse,
)

__all__ = [
    "JobSchema",
    "SkillSchema",
    "TrendAnalysisSchema",
    "TrendingSkill",
    "TrendingRole",
    "JobSearchQuery",
    "TrendQuery",
    "StatsResponse",
]
