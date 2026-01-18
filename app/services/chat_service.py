from typing import List, Dict, Any, Optional
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import SecretStr

from ..core.config import settings
from ..memory.mongo_memory import MongoConversationMemory
from ..retrieval.retrieval_service import RetrievalService
from ..models.schemas import DocumentSource
from ..models.mongodb import UserRole


class ChatService:
    """Main chat service that orchestrates conversation and retrieval"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=SecretStr(settings.openai_api_key),
        )
        self.memory = MongoConversationMemory()
        self.retrieval = RetrievalService()

        self.system_prompt = """Eres un asistente de documentación útil y experto. Tu objetivo es ayudar a los usuarios a encontrar información en la documentación disponible.

Basándote en el contexto proporcionado, responde las preguntas del usuario de manera clara y precisa. Si la información no está en el contexto, indica amablemente que no tienes esa información específica.

Directrices:
- Sé claro y conciso en tus respuestas
- Usa formato Markdown para estructurar la información
- Incluye ejemplos de código cuando sea relevante
- Siempre menciona las fuentes de información utilizadas
- Si no encuentras información relevante, sugiere temas relacionados que podrían ayudar"""

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: str = "default-user",
    ) -> Dict[str, Any]:
        """Process a chat message and return response"""
        try:
            # Get or create conversation
            if not conversation_id:
                # Check if user has a recent conversation
                latest_conversation = await self.memory.get_latest_conversation(user_id)
                if latest_conversation:
                    conversation_id = latest_conversation.conversation_id
                else:
                    conversation_id = await self.memory.create_conversation(user_id)

            # Retrieve relevant documents
            retrieved_docs = self.retrieval.retrieve_documents(message)
            context_docs = self._format_retrieved_docs(retrieved_docs)

            # Get conversation history
            recent_messages = await self.memory.get_recent_messages(
                conversation_id, limit=5
            )
            history = self._format_history(recent_messages)

            # Generate response
            response = await self._generate_response(message, context_docs, history)

            # Extract sources
            sources = self._extract_sources(retrieved_docs)

            # Save messages to memory
            await self.memory.add_message(conversation_id, UserRole.USER, message)
            await self.memory.add_message(
                conversation_id, UserRole.ASSISTANT, response, sources
            )

            return {
                "response": response,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "sources": sources,
                "retrieved_docs_count": len(retrieved_docs),
            }

        except Exception as e:
            logging.error(f"Error in chat service: {e}")
            return {
                "response": "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, intenta nuevamente.",
                "conversation_id": conversation_id or "",
                "user_id": user_id,
                "sources": [],
                "error": str(e),
            }

    async def _generate_response(
        self, question: str, context: str, history: List
    ) -> str:
        """Generate response using LLM"""
        try:
            # Create prompt
            messages = []

            # Add system message with context
            system_content = self.system_prompt
            if context:
                system_content += f"\n\nContexto de la documentación:\n{context}"

            messages.append(SystemMessage(content=system_content))

            # Add conversation history
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))

            # Add current question
            messages.append(HumanMessage(content=question))

            # Generate response
            response = await self.llm.ainvoke(messages)
            return (
                str(response.content)
                if hasattr(response, "content")
                else "Respuesta generada correctamente."
            )

        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "Lo siento, no pude generar una respuesta en este momento."

    def _format_retrieved_docs(self, docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for context"""
        if not docs:
            return "No se encontró documentación relevante para esta consulta."

        context_parts = []
        for i, doc in enumerate(docs[:3]):  # Limit to top 3 docs
            metadata = doc.get("metadata", {})
            title = metadata.get("title", "Documento sin título")
            source = metadata.get("source", "")

            context_parts.append(
                f"Documento {i + 1}: {title}\n"
                f"Fuente: {source}\n"
                f"Contenido: {doc.get('content', '')}\n"
                f"---"
            )

        return "\n".join(context_parts)

    def _format_history(self, messages: List) -> List[Dict[str, str]]:
        """Format conversation history for LLM"""
        formatted = []
        for msg in messages[-10:]:  # Last 10 messages
            formatted.append({"role": msg.role.value, "content": msg.content})
        return formatted

    def _extract_sources(
        self, retrieved_docs: List[Dict[str, Any]]
    ) -> List[DocumentSource]:
        """Extract source information from retrieved documents"""
        sources = []
        seen_sources = set()

        for doc in retrieved_docs:
            source_info = doc.get("source", {})

            # Create DocumentSource with defaults for missing fields
            source_doc = DocumentSource(
                title=source_info.get("title", "Documento sin título"),
                description=source_info.get("description", ""),
                url=source_info.get("url", ""),
                section=source_info.get("section"),
                file_path=source_info.get("file_path", ""),
            )

            source_key = (source_doc.title, source_doc.url)

            if source_key not in seen_sources:
                sources.append(source_doc)
                seen_sources.add(source_key)

        return sources

    async def get_conversation_history(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation history"""
        conversation = await self.memory.get_conversation(conversation_id)
        if not conversation:
            return {"error": "Conversation not found"}

        return conversation.to_dict_response()

    async def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation"""
        return await self.memory.delete_conversation(conversation_id)

    async def get_user_conversations(
        self, user_id: str = "default-user"
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        conversations = await self.memory.get_user_conversations(user_id)

        return [
            {
                "id": conv.conversation_id,
                "message_count": len(conv.messages) if conv.messages else 0,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "title": conv.title,
                "last_message": conv.messages[-1].content
                if conv.messages and conv.messages[-1]
                else None,
            }
            for conv in conversations
        ]

    async def get_latest_conversation(
        self, user_id: str = "default-user"
    ) -> Optional[Dict[str, Any]]:
        """Get latest conversation for a user"""
        conversation = await self.memory.get_latest_conversation(user_id)
        if not conversation:
            return None

        return conversation.to_dict_response()

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return self.retrieval.get_stats()
