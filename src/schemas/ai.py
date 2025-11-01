from pydantic import BaseModel
from typing import List, Optional, Any


class CompareSkillsRequest(BaseModel):
    skill1: str
    skill2: str


class LearningPathRequest(BaseModel):
    target_skill: str
    current_skills: List[str] = []


class QuestionRequest(BaseModel):
    question: str


class Part(BaseModel):
    kind: str
    text: Optional[str] = None
    data: Optional[List[dict]] = None


class Message(BaseModel):
    kind: str
    role: str
    parts: List[Part]
    messageId: str


class MessagePart(BaseModel):
    kind: str  # "text" or "data"
    text: Optional[str] = None
    data: Optional[List[Any]] = None
