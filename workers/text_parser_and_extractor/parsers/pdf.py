import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
import uuid # Imported for section IDs
from typing import List, Tuple, Optional
# Assuming these are correct paths based on your previous code
from workers.text_parser_and_extractor.schemas.book import Chapter, Section, BookStructure, ContentType
from workers.text_parser_and_extractor.ai_enhancements.text_classifier import text_classifier

# Configure Tesseract path if not in PATH (e.g., on Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class PDFParser:
    def __init__(self):
        self.text_classifier = text_classifier
        print("[PDFParser] Initialized PDF parser with text classifier")

    def _extract_text_with_layout(self, doc: fitz.Document) -> List[Tuple[str, float]]:
        """
        Extracts text from PDF pages, attempting to preserve block structure
        and detect font sizes for potential headlines.
        Returns a list of (text, font_size) tuples.
        """
        print(f"[PDFParser] Starting text extraction from PDF with {doc.page_count} pages")
        extracted_blocks = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            print(f"[PDFParser] Processing page {page_num + 1}/{doc.page_count}")
            # Use get_text("dict") to get structured text with font info
            blocks = page.get_text("dict")["blocks"]

            page_blocks_count = 0
            for block in blocks:
                if block["type"] == 0:  # Text block
                    # A block can contain multiple lines, we want to treat the block as a unit first
                    block_text = ""
                    max_font_size = 0.0
                    for line in block["lines"]:
                        line_text = ""
                        current_line_font_size = 0.0
                        for span in line["spans"]:
                            line_text += span["text"]
                            current_line_font_size = max(current_line_font_size, span["size"])
                        if line_text.strip():
                            block_text += line_text + "\n" # Preserve newline between lines within a block
                            max_font_size = max(max_font_size, current_line_font_size)
                    
                    if block_text.strip():
                        extracted_blocks.append((block_text.strip(), max_font_size))
                        page_blocks_count += 1
            
            print(f"[PDFParser] Page {page_num + 1}: extracted {page_blocks_count} text blocks")
        
        print(f"[PDFParser] Total extracted blocks: {len(extracted_blocks)}")
        return extracted_blocks

    def _ocr_page(self, page: fitz.Page) -> str:
        """Performs OCR on a single PDF page."""
        print(f"[PDFParser] Performing OCR on page {page.number + 1}")
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        ocr_text = pytesseract.image_to_string(img)
        print(f"[PDFParser] OCR completed for page {page.number + 1}, extracted {len(ocr_text)} characters")
        return ocr_text

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning."""
        print(f"[PDFParser] Cleaning text: {len(text)} characters")
        # Simple removal of common page artifacts (e.g., page numbers, headers/footers)
        # This is very basic and will need more sophisticated rules or ML models for real-world PDFs.
        # Example: removes lines that are just numbers or "Page X"
        cleaned_lines = []
        original_lines = text.split('\n')
        removed_lines = 0
        
        for line in original_lines:
            stripped_line = line.strip()
            if re.fullmatch(r'\d+', stripped_line): # Only numbers
                removed_lines += 1
                continue
            if re.match(r'(?i)page\s+\d+', stripped_line): # "Page X"
                removed_lines += 1
                continue
            if len(stripped_line) < 5 and not self.text_classifier.classify_text(stripped_line) in [ContentType.HEADLINE.value, ContentType.CHAPTER_TITLE.value]:
                # Heuristic: very short lines not classified as headlines might be artifacts
                removed_lines += 1
                continue
            cleaned_lines.append(stripped_line)
        
        # Join lines, then normalize multiple spaces
        text = ' '.join(cleaned_lines).strip()
        text = re.sub(r'\s+', ' ', text).strip() # Normalize multiple spaces to single space
        
        print(f"[PDFParser] Text cleaning complete: {len(original_lines)} -> {len(cleaned_lines)} lines, removed {removed_lines} lines")
        return text

    def _add_section_to_chapter(self, chapter: Chapter, content: str, content_type: str, level: Optional[int] = None):
        """Helper to add a section with a unique ID."""
        section_id = f"{chapter.chapter_id}-sec-{len(chapter.sections) + 1}-{uuid.uuid4().hex[:8]}"
        chapter.sections.append(Section(
            section_id=section_id,
            content=content,
            content_type=content_type,
            level=level
        ))
        print(f"[PDFParser] Added section to chapter {chapter.chapter_id}: {content_type} (level: {level}, content length: {len(content)})")

    def _flush_paragraph_buffer(self, paragraph_buffer: List[str], current_chapter: Chapter):
        """Flushes the accumulated paragraph content into a new section."""
        if paragraph_buffer:
            combined_paragraph = " ".join(paragraph_buffer).strip()
            if combined_paragraph:
                # Re-classify the combined paragraph to ensure its type is still correct (e.g., in case of mixed types)
                # For this feature, we assume combined text is always a paragraph
                print(f"[PDFParser] Flushing paragraph buffer with {len(paragraph_buffer)} paragraphs, total length: {len(combined_paragraph)}")
                self._add_section_to_chapter(current_chapter, combined_paragraph, ContentType.PARAGRAPH.value)
            paragraph_buffer.clear() # Clear the buffer after flushing

    def _detect_chapters_and_sections(self, extracted_blocks: List[Tuple[str, float]]) -> List[Chapter]:
        """
        Groups text blocks into chapters and sections, merging consecutive paragraphs.
        """
        print(f"[PDFParser] Starting chapter and section detection for {len(extracted_blocks)} blocks")
        chapters: List[Chapter] = []
        current_chapter: Optional[Chapter] = None
        paragraph_buffer: List[str] = [] # Buffer for accumulating paragraph content
        chapter_idx = 1

        # Heuristic for headline detection: larger font size than average
        font_sizes = [fs for _, fs in extracted_blocks if fs > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0
        print(f"[PDFParser] Average font size: {avg_font_size:.2f}")
        
        # A block is considered a potential headline if its font size is significantly larger
        # than the average, AND its length is short (e.g., less than 20 words)
        # We also prioritize AI classification for finer distinction.
        
        for i, (text_content, font_size) in enumerate(extracted_blocks):
            if i % 50 == 0:  # Log progress every 50 blocks
                print(f"[PDFParser] Processing block {i + 1}/{len(extracted_blocks)}")
                
            cleaned_text = self._clean_text(text_content)
            if not cleaned_text:
                continue

            # Classify using AI. We'll use this as the primary content type.
            ai_content_type = self.text_classifier.classify_text(cleaned_text)
            
            # --- Chapter Detection Logic ---
            # Prioritize AI's chapter title detection
            is_chapter_title_ai = (ai_content_type == ContentType.CHAPTER_TITLE.value)
            # Fallback heuristic: very large font and short text, especially if it's the first text
            is_chapter_title_heuristic = (
                (font_size > (avg_font_size * 1.5) and len(cleaned_text.split()) < 20) or # significantly larger font, short
                (len(chapters) == 0 and len(cleaned_text.split()) < 30 and font_size > avg_font_size * 1.2) # First large text block
            )
            
            is_potential_chapter_title = is_chapter_title_ai or is_chapter_title_heuristic

            if is_potential_chapter_title:
                print(f"[PDFParser] Detected potential chapter title: '{cleaned_text[:50]}...' (AI: {is_chapter_title_ai}, Heuristic: {is_chapter_title_heuristic})")
                self._flush_paragraph_buffer(paragraph_buffer, current_chapter) # Flush any pending paragraphs

                if current_chapter:
                    print(f"[PDFParser] Finalizing chapter {current_chapter.chapter_id} with {len(current_chapter.sections)} sections")
                    chapters.append(current_chapter)
                
                # Start new chapter
                current_chapter = Chapter(
                    chapter_id=f"ch-{chapter_idx}",
                    title=cleaned_text,
                    sections=[]
                )
                print(f"[PDFParser] Started new chapter {chapter_idx}: '{cleaned_text[:50]}...'")
                chapter_idx += 1
                continue # This block is the chapter title, no need to add as section immediately

            # --- Section/Paragraph Handling ---
            if not current_chapter: # If no chapter detected yet, start a default one
                current_chapter = Chapter(
                    chapter_id=f"ch-{chapter_idx}",
                    title="Introduction" if chapter_idx == 1 else f"Chapter {chapter_idx}",
                    sections=[]
                )
                print(f"[PDFParser] Created default chapter {chapter_idx}: '{current_chapter.title}'")
                chapter_idx += 1
            
            # Check if current block is a headline/list item or a paragraph
            if ai_content_type in [
                ContentType.HEADLINE.value,
            ] or ai_content_type == ContentType.FALLBACK.value: # Also flush if AI failed or fallback
                print(f"[PDFParser] Flushing paragraph buffer for content type: {ai_content_type}")
                self._flush_paragraph_buffer(paragraph_buffer, current_chapter) # Flush any pending paragraphs

                # Add the current non-paragraph block as a new section
                # Try to infer heading level for headlines
                level = None
                if ai_content_type in [ContentType.HEADLINE.value, ContentType.CHAPTER_TITLE.value]:
                    # Simple heuristic for level: larger font -> lower number level (h1 is largest)
                    # This could be improved with more detailed font size analysis or position
                    if font_size > avg_font_size * 2: level = 1
                    elif font_size > avg_font_size * 1.5: level = 2
                    elif font_size > avg_font_size * 1.2: level = 3
                    else: level = 4 # Default for detected headings
                
                self._add_section_to_chapter(current_chapter, cleaned_text, ai_content_type, level)
            else:
                # It's a paragraph or similar continuous text, add to buffer
                paragraph_buffer.append(cleaned_text)

        # Flush any remaining paragraph content after the loop ends
        if current_chapter:
            self._flush_paragraph_buffer(paragraph_buffer, current_chapter)
            print(f"[PDFParser] Finalizing final chapter {current_chapter.chapter_id} with {len(current_chapter.sections)} sections")
            chapters.append(current_chapter)

        # If no chapters were detected at all, put everything in a single default chapter
        # This handles cases where _detect_chapters_and_sections might fail to find any structure
        if not chapters and extracted_blocks:
            print("[PDFParser] No chapters detected, creating default chapter with all content")
            default_chapter = Chapter(chapter_id="ch-1", title="Full Book Content", sections=[])
            # Re-process all blocks into this single chapter, combining paragraphs
            temp_paragraph_buffer: List[str] = []
            for text_content, _ in extracted_blocks:
                cleaned_text = self._clean_text(text_content)
                if not cleaned_text:
                    continue
                ai_content_type = self.text_classifier.classify_text(cleaned_text)
                if ai_content_type == ContentType.PARAGRAPH.value:
                    temp_paragraph_buffer.append(cleaned_text)
                else:
                    if temp_paragraph_buffer:
                        self._add_section_to_chapter(default_chapter, " ".join(temp_paragraph_buffer), ContentType.PARAGRAPH.value)
                        temp_paragraph_buffer.clear()
                    self._add_section_to_chapter(default_chapter, cleaned_text, ai_content_type)
            if temp_paragraph_buffer: # Flush any remaining
                self._add_section_to_chapter(default_chapter, " ".join(temp_paragraph_buffer), ContentType.PARAGRAPH.value)
            chapters.append(default_chapter)

        print(f"[PDFParser] Chapter detection complete: {len(chapters)} chapters created")
        for i, chapter in enumerate(chapters):
            print(f"[PDFParser] Chapter {i + 1}: '{chapter.title}' with {len(chapter.sections)} sections")
        
        return chapters


    def parse(self, file_path: str, book_id: str, book_title: str = None, author: str = None) -> BookStructure:
        """Parses a PDF file and extracts structured text."""
        print(f"[PDFParser] Starting PDF parsing for file: {file_path}")
        print(f"[PDFParser] Book ID: {book_id}, Title: {book_title}, Author: {author}")
        
        try:
            doc = fitz.open(file_path)
            print(f"[PDFParser] Successfully opened PDF with {doc.page_count} pages")
            
            extracted_blocks = self._extract_text_with_layout(doc)
            print(f"[PDFParser] Initial extracted blocks count: {len(extracted_blocks)}")

            # If no text extracted directly, try OCR
            if not extracted_blocks:
                print(f"[PDFParser] No direct text found in {file_path}. Attempting OCR...")
                ocr_full_text = ""
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    ocr_full_text += self._ocr_page(page) + "\n\n" # Add double newline for paragraph separation
                
                if ocr_full_text.strip():
                    # For OCR, we split by double newlines as a heuristic for paragraphs
                    # This is a simplification; for production, you'd want OCR to give block-level data.
                    # Assign a default font size (not used for OCR'd text but required by signature)
                    extracted_blocks = [(block.strip(), 12.0) for block in ocr_full_text.split('\n\n') if block.strip()]
                    print(f"[PDFParser] OCR completed, created {len(extracted_blocks)} blocks from OCR text")
                else:
                    raise ValueError("No text or scannable images found in PDF.")

            chapters = self._detect_chapters_and_sections(extracted_blocks)
            # print(chapters) # Uncomment for detailed debug
            doc.close()
            print(f"[PDFParser] PDF parsing completed successfully")

            book_structure = BookStructure(
                book_id=book_id,
                title=book_title if book_title else "Unknown Title",
                author=author if author else "Unknown Author",
                chapters=chapters
            )
            
            print(f"[PDFParser] Created BookStructure with {len(chapters)} chapters")
            return book_structure
            
        except Exception as e:
            print(f"[PDFParser] Error parsing PDF {file_path}: {e}")
            raise

if __name__ == "__main__":
    pdf_parser = PDFParser()
    print(f"[PDFParser] Starting PDF parsing for file: workers/text_parser_and_extractor/sample.pdf")
    book_data = pdf_parser.parse("workers/text_parser_and_extractor/sample.pdf", "test-pdf-1", "My PDF Book", "PDF Author")
    with open("workers/text_parser_and_extractor/output.json", "w") as f:
        f.write(book_data.model_dump_json(indent=2))
    print(f"[PDFParser] Output written to workers/text_parser_and_extractor/output.json")