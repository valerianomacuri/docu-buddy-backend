import os
import json
from pathlib import Path
from typing import List, Dict, Any
import markdown
from bs4 import BeautifulSoup


class DocumentScraper:
    """Handles scraping and parsing of documentation files"""
    
    def __init__(self, docs_path: str = "docs"):
        self.docs_path = Path(docs_path)
        
    def load_all_documents(self) -> List[Dict[str, Any]]:
        """Load and parse all documentation files"""
        documents = []
        
        if not self.docs_path.exists():
            print(f"Documentation path {self.docs_path} does not exist")
            return documents
            
        for file_path in self.docs_path.rglob("*.md"):
            doc = self._parse_markdown_file(file_path)
            if doc:
                documents.append(doc)
                
        return documents
    
    def _parse_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first h1 or use filename
            title = self._extract_title(content, file_path)
            
            # Convert markdown to HTML for better processing
            html_content = markdown.markdown(content, extensions=['codehilite', 'tables'])
            
            # Parse HTML to extract structured content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract sections
            sections = self._extract_sections(soup)
            
            # Extract code blocks
            code_blocks = self._extract_code_blocks(content)
            
            return {
                "file_path": str(file_path),
                "relative_path": str(file_path.relative_to(self.docs_path)),
                "title": title,
                "content": content,
                "html_content": html_content,
                "sections": sections,
                "code_blocks": code_blocks,
                "word_count": len(content.split()),
                "char_count": len(content)
            }
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None # pyright: ignore[reportReturnType]
    
    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from markdown content or use filename"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fallback to filename
        return file_path.stem.replace('-', ' ').replace('_', ' ').title()
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract sections from HTML content"""
        sections = []
        
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            title = heading.get_text().strip()
            
            # Get content until next heading of same or higher level
            content = []
            next_element = heading.next_sibling
            
            while next_element:
                if next_element.name and next_element.name.startswith('h') and int(next_element.name[1]) <= level:
                    break
                if next_element.name:  # Only include tag elements, not text nodes directly
                    content.append(str(next_element))
                next_element = next_element.next_sibling
            
            sections.append({
                "level": level,
                "title": title,
                "content": " ".join(content),
                "plain_text": BeautifulSoup(" ".join(content), 'html.parser').get_text().strip()
            })
        
        return sections
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks from markdown content"""
        code_blocks = []
        
        # Extract fenced code blocks
        lines = content.split('\n')
        in_code_block = False
        code_lines = []
        language = ""
        start_line = 0
        
        for i, line in enumerate(lines):
            if line.startswith('```'):
                if not in_code_block:
                    # Start of code block
                    in_code_block = True
                    language = line[3:].strip()
                    code_lines = []
                    start_line = i + 1
                else:
                    # End of code block
                    in_code_block = False
                    code_content = '\n'.join(code_lines)
                    
                    code_blocks.append({
                        "language": language or "text",
                        "code": code_content,
                        "start_line": start_line,
                        "end_line": i,
                        "line_count": len(code_lines)
                    })
            elif in_code_block:
                code_lines.append(line)
        
        return code_blocks
    
    def chunk_document(self, document: Dict[str, Any], chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Split document into chunks for processing"""
        content = document["content"]
        words = content.split()
        chunks = []
        
        if len(words) <= chunk_size:
            # Document is small enough to be a single chunk
            chunks.append({
                **document,
                "chunk_index": 0,
                "chunk_content": content,
                "chunk_type": "full_document"
            })
            return chunks
        
        # Split into overlapping chunks
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_content = ' '.join(chunk_words)
            
            chunks.append({
                **document,
                "chunk_index": len(chunks),
                "chunk_content": chunk_content,
                "chunk_type": "section",
                "word_count": len(chunk_words)
            })
            
            # Stop if we've reached the end
            if i + chunk_size >= len(words):
                break
        
        return chunks