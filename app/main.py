from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from .core.config import settings
from .models.mongodb import Conversation, Message, User
from .routers import chat
from .services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Initialize MongoDB connection
    try:
        client = AsyncIOMotorClient(settings.mongodb_url)
        await init_beanie(
            database=client[settings.mongodb_db_name],
            document_models=[User, Conversation, Message],
            allow_index_dropping=True
        )
        print("✅ MongoDB initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize MongoDB: {e}")
        raise

    # Initialize chat service (will trigger document indexing)
    chat_service = ChatService()
    app.state.chat_service = chat_service
    print("✅ Chat service initialized successfully")

    yield

    # Cleanup if needed
    client.close()
    print("🔌 MongoDB connection closed")


app = FastAPI(
    title=settings.app_name,
    description="Backend for documentation assistant with RAG capabilities and MongoDB persistence",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "DocuBuddy Backend API 🚀", "version": "0.1.0"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name}
