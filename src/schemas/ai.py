from pydantic import BaseModel, Field
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
    data: Optional[Union[dict, List[Any]]] = None


class Message(BaseModel):
    kind: str
    role: str
    parts: List[MessagePart]
    messageId: str


class MessageParams(BaseModel):
    message: Message
    configuration: Optional[dict] = None


class ExecuteParams(BaseModel):
    messages: List[Message]
    contextId: Optional[str] = None
    taskId: Optional[str] = None


class JSONRPCParams(BaseModel):
    """Flexible params that can be either MessageParams or ExecuteParams"""

    message: Optional[Message] = None
    configuration: Optional[dict] = None
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
