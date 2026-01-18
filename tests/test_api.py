import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.models.schemas import ChatRequest


client = TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Mock chat service for testing"""
    with patch('app.routers.chat.ChatService') as mock_service:
        service_instance = Mock()
        service_instance.chat.return_value = {
            "response": "Test response",
            "conversation_id": "test-conv-id",
            "sources": []
        }
        service_instance.get_conversation_history.return_value = {
            "conversation_id": "test-conv-id",
            "messages": [],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        service_instance.get_retrieval_stats.return_value = {
            "total_documents": 10,
            "collection_name": "documentation"
        }
        service_instance.memory.get_all_conversations.return_value = []
        mock_service.return_value = service_instance
        yield service_instance


class TestChatEndpoint:
    """Test chat endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert "DocuBuddy Backend" in response.json()["message"]
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @patch('app.routers.chat.ChatService')
    def test_chat_endpoint_success(self, mock_chat_service_class, mock_chat_service):
        """Test successful chat request"""
        mock_chat_service_class.return_value = mock_chat_service
        
        chat_request = {
            "message": "Hello, how are you?",
            "conversation_id": None
        }
        
        response = client.post("/api/chat", json=chat_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert data["response"] == "Test response"
        assert data["conversation_id"] == "test-conv-id"
        
        mock_chat_service.chat.assert_called_once_with(
            message="Hello, how are you?",
            conversation_id=None
        )
    
    @patch('app.routers.chat.ChatService')
    def test_chat_endpoint_with_conversation_id(self, mock_chat_service_class, mock_chat_service):
        """Test chat request with existing conversation ID"""
        mock_chat_service_class.return_value = mock_chat_service
        
        chat_request = {
            "message": "Follow up question",
            "conversation_id": "existing-conv-id"
        }
        
        response = client.post("/api/chat", json=chat_request)
        
        assert response.status_code == 200
        mock_chat_service.chat.assert_called_once_with(
            message="Follow up question",
            conversation_id="existing-conv-id"
        )
    
    def test_chat_endpoint_invalid_request(self):
        """Test chat endpoint with invalid request"""
        # Missing required field 'message'
        chat_request = {
            "conversation_id": "test-id"
        }
        
        response = client.post("/api/chat", json=chat_request)
        assert response.status_code == 422  # Validation error
    
    @patch('app.routers.chat.ChatService')
    def test_get_history_success(self, mock_chat_service_class, mock_chat_service):
        """Test getting conversation history"""
        mock_chat_service_class.return_value = mock_chat_service
        
        response = client.get("/api/history/test-conv-id")
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
        assert data["conversation_id"] == "test-conv-id"
        
        mock_chat_service.get_conversation_history.assert_called_once_with("test-conv-id")
    
    @patch('app.routers.chat.ChatService')
    def test_get_history_not_found(self, mock_chat_service_class, mock_chat_service):
        """Test getting history for non-existent conversation"""
        mock_chat_service_class.return_value = mock_chat_service
        mock_chat_service.get_conversation_history.return_value = {
            "error": "Conversation not found"
        }
        
        response = client.get("/api/history/nonexistent-conv-id")
        
        assert response.status_code == 404
        assert "Conversation not found" in response.json()["detail"]
    
    @patch('app.routers.chat.ChatService')
    def test_clear_history_success(self, mock_chat_service_class, mock_chat_service):
        """Test clearing conversation history"""
        mock_chat_service_class.return_value = mock_chat_service
        mock_chat_service.clear_conversation.return_value = True
        
        response = client.delete("/api/history/test-conv-id")
        
        assert response.status_code == 200
        assert "cleared successfully" in response.json()["message"]
        mock_chat_service.clear_conversation.assert_called_once_with("test-conv-id")
    
    @patch('app.routers.chat.ChatService')
    def test_clear_history_not_found(self, mock_chat_service_class, mock_chat_service):
        """Test clearing non-existent conversation"""
        mock_chat_service_class.return_value = mock_chat_service
        mock_chat_service.clear_conversation.return_value = False
        
        response = client.delete("/api/history/nonexistent-conv-id")
        
        assert response.status_code == 404
    
    @patch('app.routers.chat.ChatService')
    def test_get_conversations(self, mock_chat_service_class, mock_chat_service):
        """Test getting all conversations"""
        mock_chat_service_class.return_value = mock_chat_service
        
        response = client.get("/api/conversations")
        
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        mock_chat_service.memory.get_all_conversations.assert_called_once()
    
    @patch('app.routers.chat.ChatService')
    def test_get_stats(self, mock_chat_service_class, mock_chat_service):
        """Test getting system statistics"""
        mock_chat_service_class.return_value = mock_chat_service
        
        response = client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "retrieval" in data
        assert "conversations" in data
        mock_chat_service.get_retrieval_stats.assert_called_once()
        mock_chat_service.memory.get_all_conversations.assert_called_once()


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.options("/api/chat")
        assert "access-control-allow-origin" in response.headers