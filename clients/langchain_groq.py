import logging
from typing import Dict, Any, Optional, List
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from enum import Enum
from pydantic import BaseModel, Field
from core.config import settings
import json
from workers.text_parser_and_extractor.schemas.book import ContentType

logger = logging.getLogger(__name__)

class GroqModels(str, Enum):
    LLAMA_3_1_8B_INSTANT = "llama-3.1-8b-instant"

class Section(BaseModel):
    content: str = Field(description="The actual text content of the section")
    content_type: str = Field(
        description=f"Type of content.",
        enum=ContentType.get_all_values()
    )

class PageContent(BaseModel):
    new_chapter_title: Optional[str] = Field(
        description="Chapter title if possibility of a new chapter is greater than 65%, ignore the header and footer. Otherwise, set to null",
        default=None
    )
    sections: List[Section] = Field(description="List of content sections")

class LangChainGroqClient:
    def __init__(
        self, 
        model_name: GroqModels = GroqModels.LLAMA_3_1_8B_INSTANT,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        retry_attempts: int = 3,
        retry_delay: int = 2
    ):
        self.model_name = model_name
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Initialize LangChain Groq client
        self.llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=self.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        logger.info(f"[LangChainGroqClient] Initialized with model: {model_name}")

    def parse_page_content(self, page_text: str) -> Dict[str, Any]:
        """
        Parse page content into structured JSON format using LangChain's PydanticOutputParser
        """
        # Create Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=PageContent)
        
        # Create the prompt template with format instructions
        prompt_template = PromptTemplate(
            template="""
            You are a book parsing assistant. Analyze the given page content and extract structured information.
            You ignore the headers and footers.

            {format_instructions}

            ## CRITICAL: Content Type Validation
            - You MUST use ONLY the exact content_type values listed above
            - Do NOT invent new content types
            - If unsure, use "fallback"

            ## Page Content:
            {page_text}

            ## Instructions:
            - If the page starts a new chapter, set new_chapter_title to that title
            - Otherwise, set new_chapter_title to null
            - Break down the content into logical sections
            - Classify each section by content_type using ONLY the valid values above
            - DO NOT include empty sections or sections without content
            - Each section MUST have both "content" and "content_type" fields
            - IMPORTANT: The "content" field should contain ONLY the actual book text, NOT instructions or explanations
            - DO NOT include any of these instructions in the content field
            - Return only the structured output in the specified format
            """,
            input_variables=["page_text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # Generate the prompt
        prompt = prompt_template.format(page_text=page_text)
        
        # Create messages for the LLM
        messages = [HumanMessage(content=prompt)]
        
        # Generate response with retry logic
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"[LangChainGroqClient] Parsing page content, attempt {attempt + 1}")
                
                response = self.llm.invoke(messages)
                result = response.content
                
                # Clean the raw response before parsing
                result = self._clean_raw_response(result)
                
                logger.debug(f"[LangChainGroqClient] Raw response: {result[:200]}...")
                
                # Parse the output using Pydantic parser
                try:
                    parsed_result = parser.parse(result)
                    logger.debug(f"[LangChainGroqClient] Successfully parsed output")
                    
                    # Post-process to ensure valid content types and clean data
                    result_dict = parsed_result.dict()
                    result_dict = self._clean_and_validate_result(result_dict)
                    
                    return result_dict
                    
                except Exception as parse_error:
                    logger.warning(f"[LangChainGroqClient] Pydantic parsing failed: {parse_error}")
                    logger.debug(f"[LangChainGroqClient] Attempting to extract and clean JSON manually...")
                    
                    # Try to extract JSON manually from the response
                    try:
                        import re
                        # Look for JSON-like content in the response
                        json_match = re.search(r'\{.*\}', result, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            # Try to parse as JSON
                            manual_parsed = json.loads(json_str)
                            logger.debug(f"[LangChainGroqClient] Manual JSON extraction successful")
                            
                            # Clean and validate the manual extraction
                            cleaned_parsed = self._clean_and_validate_result(manual_parsed)
                            return cleaned_parsed
                            
                    except Exception as manual_error:
                        logger.debug(f"[LangChainGroqClient] Manual JSON extraction failed: {manual_error}")
                    
                    # If all parsing fails, raise the original error
                    raise parse_error
                
            except Exception as e:
                logger.error(f"[LangChainGroqClient] Error on attempt {attempt + 1}: {e}")
                
                if attempt < self.retry_attempts - 1:
                    logger.info(f"[LangChainGroqClient] Retrying in {self.retry_delay} seconds...")
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"[LangChainGroqClient] All retry attempts failed")
                    # Return a fallback structure
                    return {
                        "new_chapter_title": None,
                        "sections": [
                            {
                                "content": page_text[:500] + "..." if len(page_text) > 500 else page_text,
                                "content_type": "fallback"
                            }
                        ]
                    }

    def _clean_and_validate_result(self, result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and validate the parsed result to ensure it meets our requirements
        """
        valid_content_types = ContentType.get_all_values()
        
        # Ensure we have the required top-level structure
        if "new_chapter_title" not in result_dict:
            result_dict["new_chapter_title"] = None
        if "sections" not in result_dict:
            result_dict["sections"] = []
        
        # Clean and validate sections
        cleaned_sections = []
        if "sections" in result_dict and isinstance(result_dict["sections"], list):
            for i, section in enumerate(result_dict["sections"]):
                # Skip empty sections or sections without required fields
                if not isinstance(section, dict) or not section:
                    logger.warning(f"[LangChainGroqClient] Skipping empty or invalid section at index {i}")
                    continue
                
                # Ensure required fields exist
                content = section.get("content", "")
                content_type = section.get("content_type", "fallback")
                
                # Skip sections with empty content
                if not content or not content.strip():
                    logger.warning(f"[LangChainGroqClient] Skipping section with empty content at index {i}")
                    continue
                
                # Clean content - remove any prompt-like text
                content = self._clean_content_text(content)
                
                # Skip if content is empty after cleaning
                if not content.strip():
                    logger.warning(f"[LangChainGroqClient] Skipping section with empty content after cleaning at index {i}")
                    continue
                
                # Validate content_type
                if content_type not in valid_content_types:
                    logger.warning(f"[LangChainGroqClient] Invalid content_type '{content_type}' found, converting to 'fallback'")
                    content_type = "fallback"
                
                # Add cleaned section
                cleaned_sections.append({
                    "content": content.strip(),
                    "content_type": content_type
                })
        
        # Update the result with cleaned sections
        result_dict["sections"] = cleaned_sections
        
        logger.debug(f"[LangChainGroqClient] Cleaned result: {len(cleaned_sections)} valid sections")
        return result_dict

    def _clean_content_text(self, content: str) -> str:
        """
        Clean content text by removing prompt-like instructions and formatting
        """
        if not content:
            return content
        
        # Remove common prompt instructions that might leak into content
        prompt_indicators = [
            "## Instructions:",
            "## Content Type Rules:",
            "## STRICT Content Type Rules:",
            "## CRITICAL:",
            "You are a book parsing assistant.",
            "Analyze the given page content",
            "Return only the structured output",
            "DO NOT include empty sections",
            "Each section MUST have",
            "Valid content_type values are:",
            "Type of content:",
            "MUST be exactly one of:",
            "If unsure, use",
            "Break down the content",
            "Classify each section",
            "If the page starts a new chapter",
            "Otherwise, set new_chapter_title to null"
        ]
        
        cleaned_content = content
        for indicator in prompt_indicators:
            if indicator in cleaned_content:
                # Remove everything from the prompt indicator onwards
                parts = cleaned_content.split(indicator)
                if len(parts) > 1:
                    cleaned_content = parts[0].strip()
                    logger.debug(f"[LangChainGroqClient] Removed prompt text starting with '{indicator}'")
        
        # Remove markdown formatting
        cleaned_content = cleaned_content.replace("```json", "").replace("```", "").strip()
        
        # Remove extra whitespace and normalize
        cleaned_content = " ".join(cleaned_content.split())
        
        return cleaned_content

    def _clean_raw_response(self, response: str) -> str:
        """
        Clean the raw response from the LLM to remove any prompt leakage
        """
        if not response:
            return response
        
        # Look for JSON content and extract only that
        import re
        
        # Try to find JSON object in the response
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        if json_matches:
            # Return the first (and usually only) JSON object found
            cleaned_response = json_matches[0]
            logger.debug(f"[LangChainGroqClient] Extracted JSON from response")
            return cleaned_response
        
        # If no JSON found, try to clean the response manually
        # Remove common prompt leakage patterns
        prompt_patterns = [
            r'## Instructions:.*?(?=\n\n|\n$|$)',
            r'## Content Type Rules:.*?(?=\n\n|\n$|$)',
            r'## STRICT Content Type Rules:.*?(?=\n\n|\n$|$)',
            r'## CRITICAL:.*?(?=\n\n|\n$|$)',
            r'You are a book parsing assistant.*?(?=\n\n|\n$|$)',
            r'Analyze the given page content.*?(?=\n\n|\n$|$)',
            r'Return only the structured output.*?(?=\n\n|\n$|$)',
            r'DO NOT include empty sections.*?(?=\n\n|\n$|$)',
            r'Each section MUST have.*?(?=\n\n|\n$|$)',
            r'Valid content_type values are:.*?(?=\n\n|\n$|$)',
            r'Type of content:.*?(?=\n\n|\n$|$)',
            r'MUST be exactly one of:.*?(?=\n\n|\n$|$)',
            r'If unsure, use.*?(?=\n\n|\n$|$)',
            r'Break down the content.*?(?=\n\n|\n$|$)',
            r'Classify each section.*?(?=\n\n|\n$|$)',
            r'If the page starts a new chapter.*?(?=\n\n|\n$|$)',
            r'Otherwise, set new_chapter_title to null.*?(?=\n\n|\n$|$)',
            r'IMPORTANT:.*?(?=\n\n|\n$|$)',
            r'DO NOT include any of these instructions.*?(?=\n\n|\n$|$)'
        ]
        
        cleaned_response = response
        for pattern in prompt_patterns:
            cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove markdown formatting
        cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
        
        # Remove extra whitespace
        cleaned_response = re.sub(r'\n\s*\n', '\n', cleaned_response)
        cleaned_response = cleaned_response.strip()
        
        logger.debug(f"[LangChainGroqClient] Cleaned raw response")
        return cleaned_response

    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Simple text generation method for backward compatibility
        """
        messages = [HumanMessage(content=prompt)]
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"[LangChainGroqClient] Error generating text: {e}")
            raise 