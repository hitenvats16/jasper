from typing import List, Optional
from bs4 import BeautifulSoup
from ebooklib import epub
from workers.text_parser_and_extractor.schemas.book import Chapter, Section, BookStructure
from workers.text_parser_and_extractor.ai_enhancements.text_classifier import text_classifier


class EPUBParser:
    def __init__(self):
        self.text_classifier = text_classifier

    def _clean_html_text(self, html_content: str) -> str:
        """Extracts and cleans text from HTML content."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted tags (scripts, styles, etc.)
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.extract()
        
        # Get text from common block-level elements.
        # This list can be expanded or refined.
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'blockquote'])
        
        cleaned_text_blocks: List[str] = []
        for element in text_elements:
            # Check if the element contains meaningful text
            text = element.get_text(separator=' ', strip=True)
            if text:
                # Classify the content type using AI
                content_type = self.text_classifier.classify_text(text)
                
                # Assign heading level if it's a headline and extractable
                level = None
                if element.name.startswith('h') and element.name[1:].isdigit():
                    level = int(element.name[1:])
                elif content_type == "headline":
                    # For non-h tags classified as headline, assign a default level or infer
                    level = 2 # A reasonable default for AI-detected headlines
                
                cleaned_text_blocks.append((text, content_type, level))

        # Join text blocks, but we need to pass them to the main parsing logic for structuring
        return cleaned_text_blocks # Return list of (text, type, level) tuples


    def parse(self, file_path: str, book_id: str, book_title: str = None, author: str = None) -> BookStructure:
        """Parses an EPUB file and extracts structured text."""
        print(f"[EPUBParser] Starting to parse EPUB file: {file_path}")
        chapters: List[Chapter] = []
        try:
            book = epub.read_epub(file_path)
            print(f"[EPUBParser] Successfully loaded EPUB file")

            # Try to get book title and author from metadata
            if not book_title:
                titles = book.get_metadata('DC', 'title')
                if titles:
                    book_title = titles[0][0]
                    print(f"[EPUBParser] Found book title in metadata: {book_title}")
            if not author:
                authors = book.get_metadata('DC', 'creator')
                if authors:
                    author = authors[0][0]
                    print(f"[EPUBParser] Found author in metadata: {author}")
            
            # Iterate through all items in the EPUB (text, images, CSS etc.)
            print(f"[EPUBParser] Processing EPUB items...")
            chapter_idx = 1
            for item in book.get_items():
                if item.get_type() == 0: # This is a text/HTML content file
                    print(f"[EPUBParser] Processing document item: {item.get_id()}")
                    html_content = item.content.decode('utf-8')
                    text_blocks_with_types = self._clean_html_text(html_content)
                    
                    if text_blocks_with_types:
                        chapter_title = None
                        
                        # Attempt to find a natural chapter title from the first headline or item title
                        if hasattr(item, 'title') and item.title:
                            chapter_title = item.title
                        
                        # Or find the first classified headline
                        for text, content_type, _ in text_blocks_with_types:
                            if content_type == "headline" and len(text.split()) < 20: # Heuristic for title
                                chapter_title = chapter_title or text # Prefer item title if available
                                break

                        current_chapter = Chapter(
                            chapter_id=f"ch-{chapter_idx}",
                            title=chapter_title if chapter_title else f"Chapter {chapter_idx}",
                            sections=[]
                        )
                        section_idx = 1
                        for text, content_type, level in text_blocks_with_types:
                            if text.strip():
                                current_chapter.sections.append(
                                    Section(
                                        section_id=f"ch-{chapter_idx}-sec-{section_idx}",
                                        content=text,
                                        content_type=content_type,
                                        level=level
                                    )
                                )
                                section_idx += 1
                        chapters.append(current_chapter)
                        print(f"[EPUBParser] Created chapter {chapter_idx-1}: '{current_chapter.title}' with {len(current_chapter.sections)} sections")
                        chapter_idx += 1

            # Fallback if no chapters found (e.g., malformed EPUB)
            if not chapters:
                print("[EPUBParser] No chapters found. Attempting full text extraction.")
                full_text_blocks: List[str] = []
                for item in book.get_items():
                    if item.get_type() == 0:
                        html_content = item.content.decode('utf-8')
                        text_blocks_with_types = self._clean_html_text(html_content)
                        for text, content_type, level in text_blocks_with_types:
                            if text.strip():
                                full_text_blocks.append((text, content_type, level))

                if full_text_blocks:
                    print(f"[EPUBParser] Creating fallback chapter with {len(full_text_blocks)} text blocks")
                    default_chapter = Chapter(chapter_id="ch-1", title="Full Book Content", sections=[])
                    for i, (text, content_type, level) in enumerate(full_text_blocks):
                        default_chapter.sections.append(
                            Section(
                                section_id=f"ch-1-sec-{i+1}",
                                content=text,
                                content_type=content_type,
                                level=level
                            )
                        )
                    chapters.append(default_chapter)
                    print(f"[EPUBParser] Created fallback chapter with {len(default_chapter.sections)} sections")
                else:
                    raise ValueError("No readable content found in EPUB.")


            print(f"[EPUBParser] Parsing completed. Total chapters: {len(chapters)}")
            return BookStructure(
                book_id=book_id,
                title=book_title if book_title else "Unknown Title",
                author=author if author else "Unknown Author",
                chapters=chapters
            )

        except Exception as e:
            print(f"[EPUBParser] Error parsing EPUB {file_path}: {e}")
            raise

if __name__ == "__main__":
    epub_parser = EPUBParser()
    book_data = epub_parser.parse("workers/text_parser_and_extractor/sample.epub", "test-epub-1", "My EPUB Book", "EPUB Author")
    print(book_data.model_dump_json(indent=2))