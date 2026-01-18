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
        # In production, get user_id from auth token
        user_id = "default-user"

        result = await chat_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=user_id,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            sources=result.get("sources", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest-conversation")
async def get_latest_conversation():
    """Get latest conversation for default user"""
    try:
        result = await chat_service.get_latest_conversation("default-user")

        if not result:
            return {"conversation_id": None, "messages": []}

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-conversations")
async def get_user_conversations():
    """Get all conversations for default user"""
    try:
        conversations = await chat_service.get_user_conversations("default-user")

        return {"conversations": conversations, "total": len(conversations)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    """Get conversation history"""
    try:
        result = await chat_service.get_conversation_history(conversation_id)

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
        success = await chat_service.clear_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Conversation cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_all_conversations():
    """Get all conversations for user"""
    try:
        conversations = await chat_service.get_user_conversations("default-user")

        return {"conversations": conversations, "total": len(conversations)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        retrieval_stats = chat_service.get_retrieval_stats()

        # For MongoDB version, get stats from service
        user_conversations = await chat_service.get_user_conversations("default-user")
        total_messages = sum(conv["message_count"] for conv in user_conversations)

        return {
            "retrieval": retrieval_stats,
            "conversations": {
                "total": len(user_conversations),
                "total_messages": total_messages,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-user")
async def get_current_user():
    """Get current user information"""
    # In production, this would extract user info from JWT token
    return {"user_id": "default-user", "name": "Usuario Demo", "is_authenticated": True}
