import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from app.scraper.document_scraper import DocumentScraper


class TestDocumentScraper:
    """Test document scraper functionality"""
    
    @pytest.fixture
    def temp_docs_dir(self):
        """Create temporary directory with test markdown files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_path = Path(temp_dir)
            
            # Create test markdown files
            (docs_path / "test1.md").write_text("""# Test Document 1

This is a test document with some content.

## Section 1

Some content in section 1.

## Section 2

Some content in section 2.

```python
def hello_world():
    print("Hello, World!")
```

This is the end of the document.
""")
            
            (docs_path / "test2.md").write_text("""# Another Document

This is another test document.

### Subsection

Some subsection content.

```javascript
console.log("Hello");
```
""")
            
            # Create subdirectory
            (docs_path / "subdir").mkdir()
            (docs_path / "subdir" / "nested.md").write_text("""# Nested Document

This document is in a subdirectory.
""")
            
            yield docs_path
    
    @pytest.fixture
    def scraper(self, temp_docs_dir):
        """Create DocumentScraper instance"""
        return DocumentScraper(docs_path=str(temp_docs_dir))
    
    def test_load_all_documents(self, scraper):
        """Test loading all markdown documents"""
        documents = scraper.load_all_documents()
        
        assert len(documents) == 3  # Should find all 3 markdown files
        
        titles = [doc["title"] for doc in documents]
        assert "Test Document 1" in titles
        assert "Another Document" in titles
        assert "Nested Document" in titles
    
    def test_parse_markdown_file(self, scraper):
        """Test parsing a single markdown file"""
        test_file = Path(scraper.docs_path) / "test1.md"
        doc = scraper._parse_markdown_file(test_file)
        
        assert doc is not None
        assert doc["title"] == "Test Document 1"
        assert "This is a test document" in doc["content"]
        assert len(doc["sections"]) > 0
        assert len(doc["code_blocks"]) > 0
    
    def test_extract_title(self, scraper):
        """Test title extraction"""
        # Test with h1 title
        content_with_h1 = "# My Title\n\nSome content"
        file_path = Path("test.md")
        title = scraper._extract_title(content_with_h1, file_path)
        assert title == "My Title"
        
        # Test without h1 (should use filename)
        content_without_h1 = "Just some content\n\nNo title here"
        title = scraper._extract_title(content_without_h1, file_path)
        assert title == "Test"
    
    def test_extract_sections(self, scraper):
        """Test section extraction"""
        html_content = """
        <h1>Main Title</h1>
        <p>Intro content</p>
        <h2>Section 1</h2>
        <p>Section 1 content</p>
        <h3>Subsection 1.1</h3>
        <p>Subsection content</p>
        <h2>Section 2</h2>
        <p>Section 2 content</p>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = scraper._extract_sections(soup)
        
        assert len(sections) == 4  # h1, h2, h3, h2
        assert sections[0]["title"] == "Main Title"
        assert sections[0]["level"] == 1
        assert sections[1]["title"] == "Section 1"
        assert sections[1]["level"] == 2
        assert sections[2]["title"] == "Subsection 1.1"
        assert sections[2]["level"] == 3
    
    def test_extract_code_blocks(self, scraper):
        """Test code block extraction"""
        content = """
        Some text before
        
        ```python
        def hello():
            print("Hello")
        ```
        
        Some text in between
        
        ```javascript
        console.log("Hello");
        ```
        
        Some text after
        """
        
        code_blocks = scraper._extract_code_blocks(content)
        
        assert len(code_blocks) == 2
        assert code_blocks[0]["language"] == "python"
        assert "def hello():" in code_blocks[0]["code"]
        assert code_blocks[1]["language"] == "javascript"
        assert "console.log" in code_blocks[1]["code"]
    
    def test_chunk_document_small(self, scraper):
        """Test chunking a small document"""
        doc = {
            "content": "This is a small document.",
            "title": "Small Doc",
            "file_path": "small.md",
            "sections": []
        }
        
        chunks = scraper.chunk_document(doc, chunk_size=100, overlap=20)
        
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "full_document"
        assert chunks[0]["chunk_content"] == doc["content"]
    
    def test_chunk_document_large(self, scraper):
        """Test chunking a large document"""
        # Create content larger than chunk size
        words = ["word"] * 200  # 200 words
        large_content = " ".join(words)
        
        doc = {
            "content": large_content,
            "title": "Large Doc",
            "file_path": "large.md",
            "sections": []
        }
        
        chunks = scraper.chunk_document(doc, chunk_size=50, overlap=10)
        
        assert len(chunks) > 1
        # Verify chunks overlap correctly
        for i, chunk in enumerate(chunks):
            assert "chunk_content" in chunk
            assert chunk["chunk_index"] == i
            assert chunk["chunk_type"] == "section"
    
    def test_load_all_documents_no_docs(self):
        """Test loading documents when directory doesn't exist"""
        scraper = DocumentScraper(docs_path="nonexistent")
        documents = scraper.load_all_documents()
        
        assert len(documents) == 0
    
    def test_chunk_document_edge_cases(self, scraper):
        """Test chunking edge cases"""
        # Test empty document
        empty_doc = {
            "content": "",
            "title": "Empty Doc",
            "file_path": "empty.md",
            "sections": []
        }
        
        chunks = scraper.chunk_document(empty_doc, chunk_size=100, overlap=20)
        assert len(chunks) == 1
        assert chunks[0]["chunk_content"] == ""