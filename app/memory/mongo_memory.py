import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from beanie import SortDirection

from ..core.config import settings
from ..models.mongodb import Conversation, Message, User, UserRole
from ..models.schemas import DocumentSource

logger = logging.getLogger(__name__)


class MongoConversationMemory:
    """MongoDB-based conversation memory service"""

    def __init__(self):
        self.max_conversation_length = settings.max_conversation_length
        self.conversation_ttl_hours = settings.conversation_ttl_hours

    async def get_or_create_user(self, user_id: str = "default-user") -> User:
        """Get existing user or create new one"""
        user = await User.find_one(User.user_id == user_id)

        if not user:
            user = User(
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={"created_by": "system", "version": "1.0.0"},
            )
            await user.save()
            logger.info(f"Created new user: {user_id}")

        return user

    async def create_conversation(
        self, user_id: str = "default-user", title: Optional[str] = None
    ) -> str:
        """Create a new conversation and return its ID"""
        user = await self.get_or_create_user(user_id)

        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title or f"Conversación {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            messages=[],
        )

        await conversation.save()

        # Update user's conversations list
        if not user.conversations:
            user.conversations = []
        user.conversations.append(Conversation.link_from_id(conversation.id))
        await user.save()

        logger.info(f"Created new conversation {conversation_id} for user {user_id}")
        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        conversation = await Conversation.find_one(
            Conversation.conversation_id == conversation_id
        )

        return conversation

    async def get_user_conversations(
        self, user_id: str = "default-user", limit: int = 50
    ) -> List[Conversation]:
        """Get all conversations for a user"""
        conversations = await Conversation.find(
            Conversation.user_id == user_id
        ).sort([("updated_at", SortDirection.DESCENDING)]).to_list()
        return conversations

    async def get_latest_conversation(
        self, user_id: str = "default-user"
    ) -> Optional[Conversation]:
        """Get the most recent conversation for a user"""
        conversation = await (
            Conversation.find(Conversation.user_id == user_id)
            .sort([("updated_at", SortDirection.DESCENDING)])
            .first_or_none()
        )
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: UserRole,
        content: str,
        sources: Optional[List[DocumentSource]] = None,
    ) -> Optional[Message]:
        """Add a message to a conversation"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found")
            return None

        try:
            message = Message(role=role, content=content, sources=sources or [])

            # Add to embedded messages
            if not conversation.messages:
                conversation.messages = []
            conversation.messages.append(message)

            # Trim conversation if it gets too long
            if len(conversation.messages) > self.max_conversation_length:
                # Keep first message (for context) and last N messages
                recent_messages = conversation.messages[
                    -(self.max_conversation_length - 1) :
                ]
                conversation.messages = [conversation.messages[0]] + recent_messages

            # Update timestamps
            conversation.updated_at = datetime.utcnow()

            # Save to MongoDB
            await conversation.save()

            logger.info(f"Added {role.value} message to conversation {conversation_id}")
            return message

        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            return None

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 10
    ) -> List[Message]:
        """Get recent messages from a conversation"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation or not conversation.messages:
            return []

        messages = conversation.messages[-limit:] if conversation.messages else []
        return messages

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            conversation = await Conversation.find_one(
                Conversation.conversation_id == conversation_id
            )

            if conversation:
                await conversation.delete()
                logger.info(f"Deleted conversation {conversation_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    async def clear_user_conversations(self, user_id: str = "default-user") -> int:
        """Clear all conversations for a user"""
        try:
            conversations = await Conversation.find(
                Conversation.user_id == user_id
            ).to_list()

            count = len(conversations)
            for conv in conversations:
                await conv.delete()

            logger.info(f"Cleared {count} conversations for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error clearing conversations for user {user_id}: {e}")
            return 0

    async def cleanup_old_conversations(self):
        """Remove conversations older than TTL"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(
                hours=self.conversation_ttl_hours
            )

            old_conversations = await Conversation.find(
                Conversation.updated_at < cutoff_time
            ).to_list()

            count = len(old_conversations)
            for conv in old_conversations:
                await conv.delete()

            if count > 0:
                logger.info(f"Cleaned up {count} old conversations")

        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    async def get_all_conversations(self) -> List[Conversation]:
        """Get all conversations (for admin/stats purposes)"""
        conversations = await (
            Conversation.find()
            .sort([("updated_at", SortDirection.DESCENDING)])
            .limit(100)
            .to_list()
        )
        return conversations

    async def get_conversation_stats(
        self, user_id: str = "default-user"
    ) -> Dict[str, Any]:
        """Get statistics for a user"""
        try:
            conversations = await Conversation.find(
                Conversation.user_id == user_id
            ).to_list()

            total_messages = sum(
                len(conv.messages) if conv.messages else 0 for conv in conversations
            )

            return {
                "user_id": user_id,
                "total_conversations": len(conversations),
                "total_messages": total_messages,
                "latest_conversation_updated": (
                    max(conv.updated_at for conv in conversations).isoformat()
                    if conversations
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "total_conversations": 0,
                "total_messages": 0,
                "error": str(e),
            }
