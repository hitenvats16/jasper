import fitz 
import uuid
import logging
from typing import List, Optional
from workers.text_parser_and_extractor.schemas.book import Chapter, Section, BookStructure
from clients.langchain_groq import LangChainGroqClient, GroqModels
from utils.text import escape_page_text


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PDFParser')


class PDFParser:
    def __init__(self):
        logger.info("[PDFParser] Initialized PDF parser")
        self.llm_client = LangChainGroqClient(
            model_name=GroqModels.LLAMA_3_1_8B_INSTANT,
            temperature=1.0,
            max_tokens=4096,
            retry_attempts=3,
            retry_delay=2
        )

    def _extract_text_blocks(self, doc: fitz.Document) -> List[str]:
        logger.info(f"[PDFParser] Extracting pages from PDF with {doc.page_count} pages")
        pages = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text").strip()
            if not text:
                logger.info(f"[PDFParser] Page {page_num+1} is likely an image. Inserting placeholder.")
                text = "[IMAGE PAGE - NO TEXT]"
            pages.append(text)
        return pages

    def parse(self, pdf_buffer: bytes, book_id: str, book_title: str = None, author: str = None) -> BookStructure:
        logger.info(f"[PDFParser] Parsing PDF buffer for book: {book_id}")
        try:
            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
            logger.debug(f"[PDFParser] Successfully opened PDF with {doc.page_count} pages")
        except Exception as e:
            logger.error(f"[PDFParser] Failed to open PDF buffer for book {book_id}: {str(e)}")
            raise
        
        pages = self._extract_text_blocks(doc)
        doc.close()
        logger.debug(f"[PDFParser] Extracted {len(pages)} text blocks from PDF")

        chapters: List[Chapter] = []
        current_chapter: Optional[Chapter] = None
        chapter_idx = 1

        for i, page_text in enumerate(pages):
            logger.info(f"[PDFParser] Processing page {i+1}/{len(pages)}")
            
            try:
                escaped_text = escape_page_text(page_text)
                logger.debug(f"[PDFParser] Escaped text length: {len(escaped_text)} characters")
                
                # Use the new structured parsing method
                parsed = self.llm_client.parse_page_content(escaped_text)
                
                if not parsed:
                    logger.warning(f"[PDFParser] No structured data returned from LLM for page {i+1}")
                    continue
                    
                logger.debug(f"[PDFParser] Successfully parsed page {i+1}: {type(parsed)}")
                
            except Exception as e:
                logger.error(f"[PDFParser] Error processing page {i+1}: {str(e)}")
                logger.warning(f"[PDFParser] Skipping page {i+1} due to error")
                continue

            if parsed.get("new_chapter_title"):
                if current_chapter:
                    chapters.append(current_chapter)
                    logger.debug(f"[PDFParser] Completed chapter: {current_chapter.title}")
                current_chapter = Chapter(
                    chapter_id=f"ch-{chapter_idx}",
                    title=parsed["new_chapter_title"],
                    sections=[]
                )
                logger.info(f"[PDFParser] Started new chapter {chapter_idx}: {parsed['new_chapter_title']}")
                chapter_idx += 1

            if not current_chapter:
                # Start first chapter if not yet started
                current_chapter = Chapter(
                    chapter_id=f"ch-{chapter_idx}",
                    title="Introduction",
                    sections=[]
                )
                logger.info(f"[PDFParser] Started first chapter: Introduction")
                chapter_idx += 1

            for section in parsed["sections"]:
                try:
                    # Validate content_type and convert to fallback if invalid
                    content_type = section.get("content_type", "fallback")
                    valid_types = ["chapter_title", "headline", "paragraph", "bullet", "list_item", "fallback"]
                    
                    if content_type not in valid_types:
                        logger.warning(f"[PDFParser] Invalid content_type '{content_type}', converting to 'fallback'")
                        content_type = "fallback"
                    
                    current_chapter.sections.append(Section(
                        section_id=f"{current_chapter.chapter_id}-sec-{len(current_chapter.sections)+1}-{uuid.uuid4().hex[:8]}",
                        content=section.get("content", ""),
                        content_type=content_type,
                        page_number=i + 1,  # Page number (1-indexed)
                    ))
                    logger.debug(f"[PDFParser] Added section to chapter {current_chapter.chapter_id}: {content_type} - {section.get('content', '')[:50]}... (Page {i+1})")
                    
                except Exception as e:
                    logger.error(f"[PDFParser] Error processing section: {e}")
                    # Add a fallback section if there's an error
                    current_chapter.sections.append(Section(
                        section_id=f"{current_chapter.chapter_id}-sec-{len(current_chapter.sections)+1}-{uuid.uuid4().hex[:8]}",
                        content=section.get("content", "Error processing content"),
                        content_type="fallback",
                        page_number=i + 1,  # Page number (1-indexed)
                        raw_text=page_text  # Raw text from the page
                    ))

        if current_chapter:
            chapters.append(current_chapter)
            logger.debug(f"[PDFParser] Added final chapter: {current_chapter.title}")

        book_structure = BookStructure(
            book_id=book_id,
            title=book_title or "Unknown Title",
            author=author or "Unknown Author",
            chapters=chapters
        )

        total_sections = sum(len(chapter.sections) for chapter in chapters)
        logger.info(f"[PDFParser] Finished parsing. Total chapters: {len(chapters)}, Total sections: {total_sections}")
        return book_structure
