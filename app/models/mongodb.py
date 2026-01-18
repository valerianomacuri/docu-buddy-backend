from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field, ConfigDict
from beanie import Document, Link, BackLink
from enum import Enum

from .schemas import DocumentSource


class UserRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class User(Document):
    """User model for MongoDB"""

    model_config = ConfigDict(collection="users", validate_assignment=True)

    user_id: str = Field(..., unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Links to conversations
    conversations: Optional[List[Link["Conversation"]]] = Field(default_factory=list)

    class Settings:
        indexes = ["user_id", "created_at"]


class Message(Document):
    """Message model for MongoDB"""

    model_config = ConfigDict(collection="messages")

    id: str = Field(default_factory=lambda: f"msg_{datetime.utcnow().timestamp()}")
    role: UserRole = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: Optional[List[DocumentSource]] = Field(default_factory=list)

    # Link to parent conversation
    conversation: Optional[Link["Conversation"]] = Field(None)

    class Settings:
        indexes = ["conversation_id", "timestamp"]


class Conversation(Document):
    """Conversation model for MongoDB"""

    model_config = ConfigDict(collection="conversations")

    conversation_id: str = Field(..., unique=True, index=True)
    user_id: str = Field(..., index=True)
    title: Optional[str] = Field(None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Link to user
    user: Optional[Link[User]] = Field(None)

    # Embedded messages (for performance)
    messages: Optional[List[Message]] = Field(default_factory=list)

    class Settings:
        indexes = ["conversation_id", "user_id", "created_at", "updated_at"]

    async def add_message(
        self,
        role: UserRole,
        content: str,
        sources: Optional[List[DocumentSource]] = None,
    ) -> Message:
        """Add a message to this conversation"""
        message = Message(role=role, content=content, sources=sources or [])

        # Add to embedded messages
        if not self.messages:
            self.messages = []
        self.messages.append(message)

        # Update timestamps
        self.updated_at = datetime.utcnow()

        # Save to MongoDB (this will also save the embedded messages)
        await self.save()

        return message

    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get messages from this conversation"""
        if not self.messages:
            return []

        messages = self.messages
        if limit:
            messages = messages[-limit:]

        return messages

    def to_dict_response(self) -> Dict[str, Any]:
        """Convert conversation to response dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": [source.dict() for source in (msg.sources or [])],
                }
                for msg in (self.messages or [])
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
        }
