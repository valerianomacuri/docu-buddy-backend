from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DocumentChunk(BaseModel):
    """Represents a chunk of processed documentation"""
    id: str
    content: str
    metadata: dict
    source_file: str
    chunk_index: int
    created_at: datetime = datetime.utcnow()


class DocumentSource(BaseModel):
    """Source information for documentation references"""
    title: str
    description: str
    url: str
    section: Optional[str] = None
    file_path: str


class ChatMessage(BaseModel):
    """Represents a chat message"""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = datetime.utcnow()
    sources: Optional[List[DocumentSource]] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str
    conversation_id: str
    sources: Optional[List[DocumentSource]] = None


class Conversation(BaseModel):
    """Represents a conversation thread"""
    id: str
    messages: List[ChatMessage]
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()