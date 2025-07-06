from abc import ABC, abstractmethod
from typing import List, Tuple, Iterator
import spacy
import re


class TextSplittingStrategy(ABC):
    """Protocol for text chunking strategies."""

    @abstractmethod
    def chunk_text(self, text: str, **kwargs) -> List[Tuple[str, bool]]:
        ...

    @abstractmethod
    def chunk_stream(self, text: str, **kwargs) -> Iterator[Tuple[str, bool]]:
        ...
        


class QuoteAwareTTSTextSplittingStrategy(TextSplittingStrategy):
    def __init__(self, model: str = "en_core_web_sm", max_tokens: int = 50):
        try:
            self.nlp = spacy.load(model, disable=["ner", "tagger"])
        except OSError:
            print(f"Downloading spaCy model '{model}'...")
            from spacy.cli import download
            download(model)
            self.nlp = spacy.load(model, disable=["ner", "tagger"])

        self.max_tokens = max_tokens

    def chunk_text(self, text: str, **kwargs) -> List[Tuple[str, bool]]:
        return list(self.chunk_stream(text, **kwargs))

    def chunk_stream(self, text: str, **kwargs) -> Iterator[Tuple[str, bool]]:
        paragraphs = re.split(r'\n\s*\n', text.strip())
        buffer = []
        token_count = 0
        quote_balance = 0

        for para in paragraphs:
            if not para.strip():
                continue

            doc = self.nlp(para)
            sentences = [sent.text.strip() for sent in doc.sents]

            for sent in sentences:
                sent_doc = self.nlp(sent)
                sent_tokens = len(sent_doc)
                quote_balance += self._quote_delta(sent)

                buffer.append(sent)
                token_count += sent_tokens

                # If we hit token limit and we're not inside an open quote block
                if token_count >= self.max_tokens and quote_balance == 0:
                    chunk = " ".join(buffer).strip()
                    yield (chunk, self._ends_with_paragraph(buffer))
                    buffer = []
                    token_count = 0
                    quote_balance = 0

            # End of paragraph — flush if anything remains
            if buffer:
                chunk = " ".join(buffer).strip()
                yield (chunk, True)
                buffer = []
                token_count = 0
                quote_balance = 0

        if buffer:
            yield (" ".join(buffer).strip(), True)

    def _quote_delta(self, text: str) -> int:
        """
        Track quote state using open/close quotes. Returns 1 if inside quote, 0 if balanced.
        """
        quotes = ['"', '“', '”']
        return sum(text.count(q) for q in quotes) % 2

    def _ends_with_paragraph(self, buffer: List[str]) -> bool:
        if not buffer:
            return False
        last = buffer[-1]
        return last.endswith(('.', '?', '!', '."', '?”', '!”', '"'))
