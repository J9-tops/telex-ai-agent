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

from src.schemas.ai import (
    CompareSkillsRequest,
    LearningPathRequest,
    QuestionRequest,
    Message,
    MessagePart,
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
    "QuestionRequest",
    "CompareSkillsRequest",
    "LearningPathRequest",
    "Message",
    "MessagePart",
]
