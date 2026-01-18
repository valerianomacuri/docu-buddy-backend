from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, Link
from pydantic import Field

from .schemas import DocumentSource


class UserRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        # Le decimos a Pydantic que lo trate como un string
        return core_schema.str_schema()


class User(Document):
    """User model for MongoDB"""

    class Settings:
        name = "users"
        use_state_management = True
        indexes = ["user_id", "created_at"]

    user_id: Indexed(str, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversations: List[Link["Conversation"]] = Field(default_factory=list)



class Message(Document):
    """Message model for MongoDB"""

    class Settings:
        name = "messages"
        use_state_management = True
        indexes = ["conversation_id", "timestamp"]

    message_id: str = Field(
        default_factory=lambda: f"msg_{datetime.utcnow().timestamp()}"
    )
    role: UserRole
    content: str = Field(min_length=1, max_length=10000)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[DocumentSource] = Field(default_factory=list)


class Conversation(Document):
    """Conversation model for MongoDB"""

    class Settings:
        name = "conversations"
        use_state_management = True
        indexes = ["conversation_id", "user_id", "created_at", "updated_at"]

    conversation_id: Indexed(str, unique=True)
    user_id: Indexed(str)
    title: Optional[str] = Field(None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Embedded messages (for performance)
    messages: List[Message] = Field(default_factory=list)

    async def add_message(
        self,
        role: UserRole,
        content: str,
        sources: Optional[List[DocumentSource]] = None,
    ) -> Message:
        """Add a message to this conversation"""
        message = Message(role=role, content=content, sources=sources or [])

        # Add to embedded messages
        self.messages.append(message)

        # Update timestamps
        self.updated_at = datetime.utcnow()

        # Save to MongoDB (this will also save embedded messages)
        await self.save()

        return message

    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get messages from this conversation"""
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
                    "id": msg.message_id,
                    "role": msg.role,  # ya funciona
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": [source.dict() for source in msg.sources],
                }
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
        }
