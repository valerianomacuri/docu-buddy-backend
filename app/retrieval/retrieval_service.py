import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr

from ..core.config import settings
from ..scraper.document_scraper import DocumentScraper


class RetrievalService:
    """Handles document indexing and retrieval using ChromaDB"""

    def __init__(self):
        # Crear embeddings usando la API Key como string
        self.embeddings = OpenAIEmbeddings(
            api_key=SecretStr(settings.openai_api_key),
            model="text-embedding-3-small"
        )
        self.vector_store: Optional[Chroma] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )
        self.scraper = DocumentScraper(docs_path=settings.docs_path)
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize ChromaDB vector store"""
        try:
            self.vector_store = Chroma(
                collection_name=settings.chroma_collection_name,
                embedding_function=self.embeddings,
                persist_directory="./chroma_db"
            )
            # Index documents if collection is empty
            if self._is_collection_empty():
                self.index_documents()
        except Exception as e:
            logging.error(f"Error initializing vector store: {e}")
            raise

    def _is_collection_empty(self) -> bool:
        """Check if the collection is empty"""
        try:
            # Intentar obtener un documento
            result = self.vector_store._collection.get(limit=1)  # pyright: ignore
            return not bool(result.get("ids"))
        except Exception:
            return True

    def _create_langchain_docs(self, chunks: List[Any]) -> List[Document]:
        """Convert chunks into LangChain Documents safely"""
        langchain_docs = []

        for chunk in chunks:
            # Si el chunk es una tupla (chunk, ...) tomar solo el primer elemento
            if isinstance(chunk, tuple):
                chunk = chunk[0]

            # Manejar chunk_index seguro
            try:
                chunk_index = int(chunk.get("chunk_index") or 0)
            except (ValueError, TypeError):
                chunk_index = 0

            metadata = {
                "source": chunk.get("relative_path", ""),
                "title": chunk.get("title", ""),
                "file_path": chunk.get("file_path", ""),
                "chunk_index": chunk_index,
                "chunk_type": chunk.get("chunk_type", "section"),
            }

            sections = chunk.get("sections", [])
            if sections:
                metadata["sections"] = ", ".join([s.get("title", "") for s in sections])

            doc = Document(page_content=chunk.get("chunk_content", ""), metadata=metadata)

            # Filtrar metadata
            doc = filter_complex_metadata([doc])[0]
            langchain_docs.append(doc)

        return langchain_docs


    def index_documents(self):
        """Index all documentation files"""
        logging.info("Starting document indexing...")
        documents = self.scraper.load_all_documents()
        if not documents:
            logging.warning("No documents found to index")
            return

        all_chunks = []
        for doc in documents:
            try:
                chunks = self.scraper.chunk_document(doc)
                all_chunks.extend(chunks)
            except Exception as e:
                logging.error(f"Error parsing {doc.get('file_path', 'unknown')}: {e}")

        langchain_docs = self._create_langchain_docs(all_chunks)

        if langchain_docs:
            self.vector_store.add_documents(langchain_docs)
            logging.info(f"Indexed {len(langchain_docs)} document chunks")
        else:
            logging.warning("No document chunks created")

    def retrieve_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query"""
        if not self.vector_store:
            logging.error("Vector store not initialized")
            return []

        top_k = top_k or settings.retrieval_top_k

        try:
            docs = self.vector_store.similarity_search_with_score(query, k=top_k)
            results = []

            for doc, score in docs:
                sections = doc.metadata.get("sections")
                section_name = sections.split(", ")[0] if isinstance(sections, str) and sections else None

                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score,
                    "source": {
                        "title": doc.metadata.get("title", "Unknown"),
                        "description": f"Section from {doc.metadata.get('title', 'document')}",
                        "url": f"/docs/{doc.metadata.get('source', '').replace('.md', '')}",
                        "section": section_name,
                        "file_path": doc.metadata.get("file_path", "")
                    }
                }
                results.append(result)

            return results
        except Exception as e:
            logging.error(f"Error retrieving documents: {e}")
            return []

    def add_document(self, file_path: str, content: str) -> bool:
        """Add a single document to the index"""
        try:
            doc_dict = {
                "file_path": file_path,
                "relative_path": Path(file_path).name,
                "title": Path(file_path).stem.replace('-', ' ').replace('_', ' ').title(),
                "content": content,
                "sections": [],
                "code_blocks": []
            }

            chunks = self.scraper.chunk_document(doc_dict)
            langchain_docs = self._create_langchain_docs(chunks)

            if langchain_docs:
                self.vector_store.add_documents(langchain_docs)
                return True

        except Exception as e:
            logging.error(f"Error adding document: {e}")

        return False

    def search_by_source(self, source_file: str) -> List[Dict[str, Any]]:
        """Search for documents from a specific source file"""
        if not self.vector_store:
            return []

        try:
            filter_dict = {"source": source_file}
            docs = self.vector_store.get(where=filter_dict)
            results = []

            for i, doc_id in enumerate(docs.get("ids", [])):
                result = {
                    "content": docs["documents"][i] if i < len(docs["documents"]) else "",
                    "metadata": docs["metadatas"][i] if docs.get("metadatas") and i < len(docs["metadatas"]) else {},
                    "id": doc_id
                }
                results.append(result)

            return results

        except Exception as e:
            logging.error(f"Error searching by source: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed documents"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}

        try:
            collection_stats = self.vector_store._collection.get()
            return {
                "total_documents": len(collection_stats.get("ids", [])),
                "collection_name": settings.chroma_collection_name,
                "embedding_model": "text-embedding-3-small"
            }
        except Exception as e:
            logging.error(f"Error getting stats: {e}")
            return {"error": str(e)}
