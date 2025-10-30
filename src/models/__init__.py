"""Data models for the application"""

from src.models.job import Job, Skill, TrendAnalysis, SkillTrend, Base
from src.models.a2a import (
    A2AMessage,
    MessagePart,
    TaskResult,
    TaskStatus,
    Artifact,
    JSONRPCRequest,
    JSONRPCResponse,
)

__all__ = [
    "Job",
    "Skill",
    "TrendAnalysis",
    "SkillTrend",
    "Base",
    "A2AMessage",
    "MessagePart",
    "TaskResult",
    "TaskStatus",
    "Artifact",
    "JSONRPCRequest",
    "JSONRPCResponse",
]
