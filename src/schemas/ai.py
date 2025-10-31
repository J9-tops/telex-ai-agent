from pydantic import BaseModel
from typing import List, Optional


class CompareSkillsRequest(BaseModel):
    skill1: str
    skill2: str


class LearningPathRequest(BaseModel):
    target_skill: str
    current_skills: List[str] = []


class QuestionRequest(BaseModel):
    question: str
