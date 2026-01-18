import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import json

from app.memory.conversation_memory import ConversationMemory
from app.models.schemas import ChatMessage


class TestConversationMemory:
    """Test conversation memory functionality"""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary directory for memory storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def memory(self, temp_memory_dir):
        """Create ConversationMemory instance with temp directory"""
        return ConversationMemory(storage_path=temp_memory_dir)
    
    def test_create_conversation(self, memory):
        """Test creating a new conversation"""
        conversation_id = memory.create_conversation()
        
        assert conversation_id is not None
        assert len(conversation_id) > 0
        
        # Check conversation exists
        conversation = memory.get_conversation(conversation_id)
        assert conversation is not None
        assert conversation.id == conversation_id
        assert len(conversation.messages) == 0
    
    def test_add_message(self, memory):
        """Test adding a message to conversation"""
        conversation_id = memory.create_conversation()
        
        message = memory.add_message(
            conversation_id=conversation_id,
            role="user",
            content="Hello, world!"
        )
        
        assert message is not None
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.id is not None
        
        # Check message is in conversation
        conversation = memory.get_conversation(conversation_id)
        assert len(conversation.messages) == 1
        assert conversation.messages[0].content == "Hello, world!"
    
    def test_add_message_with_sources(self, memory):
        """Test adding a message with sources"""
        conversation_id = memory.create_conversation()
        
        sources = [
            {
                "title": "Test Document",
                "description": "Test description",
                "url": "/test"
            }
        ]
        
        message = memory.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content="Here's your answer",
            sources=sources
        )
        
        assert message is not None
        assert message.sources == sources
    
    def test_get_recent_messages(self, memory):
        """Test getting recent messages from conversation"""
        conversation_id = memory.create_conversation()
        
        # Add multiple messages
        for i in range(5):
            memory.add_message(
                conversation_id=conversation_id,
                role="user",
                content=f"Message {i}"
            )
        
        recent = memory.get_recent_messages(conversation_id, limit=3)
        assert len(recent) == 3
        assert recent[0].content == "Message 2"  # Should get last 3 messages
        assert recent[2].content == "Message 4"
    
    def test_conversation_trimming(self, temp_memory_dir):
        """Test that conversations are trimmed when they get too long"""
        # Override max length for testing
        with patch('app.memory.conversation_memory.settings') as mock_settings:
            mock_settings.max_conversation_length = 3
            
            memory = ConversationMemory(storage_path=temp_memory_dir)
            conversation_id = memory.create_conversation()
            
            # Add first message
            memory.add_message(conversation_id, "user", "First message")
            
            # Add 3 more messages (total 4)
            for i in range(3):
                memory.add_message(conversation_id, "user", f"Message {i}")
            
            conversation = memory.get_conversation(conversation_id)
            # Should have first message + last 2 messages = 3 total
            assert len(conversation.messages) == 3
            assert conversation.messages[0].content == "First message"
            assert conversation.messages[1].content == "Message 1"
            assert conversation.messages[2].content == "Message 2"
    
    def test_delete_conversation(self, memory):
        """Test deleting a conversation"""
        conversation_id = memory.create_conversation()
        memory.add_message(conversation_id, "user", "Test message")
        
        # Verify conversation exists
        assert memory.get_conversation(conversation_id) is not None
        
        # Delete conversation
        success = memory.delete_conversation(conversation_id)
        assert success is True
        
        # Verify conversation is gone
        assert memory.get_conversation(conversation_id) is None
    
    def test_delete_nonexistent_conversation(self, memory):
        """Test deleting a conversation that doesn't exist"""
        success = memory.delete_conversation("nonexistent-id")
        assert success is False
    
    def test_persistence(self, temp_memory_dir):
        """Test that conversations are persisted to disk"""
        # Create memory and add conversation
        memory1 = ConversationMemory(storage_path=temp_memory_dir)
        conversation_id = memory1.create_conversation()
        memory1.add_message(conversation_id, "user", "Test message")
        
        # Create new memory instance (should load from disk)
        memory2 = ConversationMemory(storage_path=temp_memory_dir)
        conversation = memory2.get_conversation(conversation_id)
        
        assert conversation is not None
        assert len(conversation.messages) == 1
        assert conversation.messages[0].content == "Test message"
    
    def test_get_all_conversations(self, memory):
        """Test getting all conversations"""
        # Create multiple conversations
        conv1 = memory.create_conversation()
        conv2 = memory.create_conversation()
        
        memory.add_message(conv1, "user", "Message 1")
        memory.add_message(conv2, "user", "Message 2")
        
        all_convs = memory.get_all_conversations()
        assert len(all_convs) == 2
        
        conv_ids = [conv.id for conv in all_convs]
        assert conv1 in conv_ids
        assert conv2 in conv_ids