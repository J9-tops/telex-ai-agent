from pydantic import BaseModel, field_validator
from typing import List, Optional, Any, Union


class CompareSkillsRequest(BaseModel):
    skill1: str
    skill2: str


class LearningPathRequest(BaseModel):
    target_skill: str
    current_skills: List[str] = []


class QuestionRequest(BaseModel):
    question: str


class MessagePart(BaseModel):
    kind: str
    text: Optional[str] = None
    data: Optional[Any] = None

    class Config:
        extra = "allow"


class Message(BaseModel):
    kind: str
    role: str
    parts: List[MessagePart]
    messageId: str

    class Config:
        extra = "allow"


class JSONRPCParams(BaseModel):
    # For message/send method
    message: Optional[Message] = None
    configuration: Optional[Any] = None

    # For execute method
    messages: Optional[List[Message]] = None
    contextId: Optional[str] = None
    taskId: Optional[str] = None

    class Config:
        extra = "allow"


class JSONRPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: JSONRPCParams

    class Config:
        extra = "allow"


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Any] = None
    error: Optional[dict] = None
