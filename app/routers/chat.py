from fastapi import APIRouter, HTTPException
from typing import List

from ..models.schemas import ChatRequest, ChatResponse
from ..services.chat_service import ChatService


router = APIRouter(prefix="/api", tags=["chat"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Send a message and get a response"""
    try:
        result = await chat_service.chat(
            message=request.message,
            conversation_id=request.conversation_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            sources=result.get("sources", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    """Get conversation history"""
    try:
        result = chat_service.get_conversation_history(conversation_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{conversation_id}")
async def clear_history(conversation_id: str):
    """Clear conversation history"""
    try:
        success = chat_service.clear_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_all_conversations():
    """Get all conversations"""
    try:
        conversations = chat_service.memory.get_all_conversations()
        
        return {
            "conversations": [
                {
                    "id": conv.id,
                    "message_count": len(conv.messages),
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "last_message": conv.messages[-1].content if conv.messages else None
                }
                for conv in conversations
            ],
            "total": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        retrieval_stats = chat_service.get_retrieval_stats()
        conversations = chat_service.memory.get_all_conversations()
        
        return {
            "retrieval": retrieval_stats,
            "conversations": {
                "total": len(conversations),
                "total_messages": sum(len(conv.messages) for conv in conversations)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))