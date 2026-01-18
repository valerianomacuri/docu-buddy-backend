from typing import Dict, List, Any, Optional
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..models.schemas import Conversation, ChatMessage


class ConversationMemory:
    """Manages conversation history with persistence"""
    
    def __init__(self, storage_path: str = "memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.conversations: Dict[str, Conversation] = {}
        self._load_conversations()
    
    def create_conversation(self) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            messages=[]
        )
        self.conversations[conversation_id] = conversation
        self._save_conversation(conversation)
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self.conversations.get(conversation_id)
    
    def add_message(self, conversation_id: str, role: str, content: str, sources: Optional[List[Dict]] = None) -> Optional[ChatMessage]:
        """Add a message to a conversation"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        message = ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            sources=sources
        )
        
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()
        
        # Trim conversation if it gets too long
        from ..core.config import settings
        if len(conversation.messages) > settings.max_conversation_length:
            # Keep the first message (for context) and last N messages
            recent_messages = conversation.messages[-(settings.max_conversation_length-1):]
            conversation.messages = [conversation.messages[0]] + recent_messages
        
        self._save_conversation(conversation)
        return message
    
    def get_recent_messages(self, conversation_id: str, limit: int = 10) -> List[ChatMessage]:
        """Get recent messages from a conversation"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        return conversation.messages[-limit:]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            conversation_file = self.storage_path / f"{conversation_id}.json"
            if conversation_file.exists():
                conversation_file.unlink()
            return True
        return False
    
    def cleanup_old_conversations(self):
        """Remove conversations older than TTL"""
        from ..core.config import settings
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.conversation_ttl_hours)
        
        to_delete = []
        for conv_id, conversation in self.conversations.items():
            if conversation.updated_at < cutoff_time:
                to_delete.append(conv_id)
        
        for conv_id in to_delete:
            self.delete_conversation(conv_id)
    
    def _load_conversations(self):
        """Load conversations from disk"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    conversation = Conversation(**data)
                    self.conversations[conversation.id] = conversation
            except Exception as e:
                print(f"Error loading conversation from {file_path}: {e}")
    
    def _save_conversation(self, conversation: Conversation):
        """Save a conversation to disk"""
        conversation_file = self.storage_path / f"{conversation.id}.json"
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation.dict(), f, default=str, indent=2)
        except Exception as e:
            print(f"Error saving conversation to {conversation_file}: {e}")
    
    def get_all_conversations(self) -> List[Conversation]:
        """Get all conversations"""
        return list(self.conversations.values())