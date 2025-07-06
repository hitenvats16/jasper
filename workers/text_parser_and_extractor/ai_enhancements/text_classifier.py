import os
from transformers import pipeline
from dotenv import load_dotenv
from workers.text_parser_and_extractor.schemas.book import ContentType

load_dotenv()

class TextClassifier:
    """
    A simple AI-powered text classifier to identify headlines vs. paragraphs.
    Uses a pre-trained Hugging Face model for zero-shot classification.
    """
    _instance = None

    def __new__(cls, candidate_labels=None):
        if cls._instance is None:
            cls._instance = super(TextClassifier, cls).__new__(cls)
            # Initialize the NLP pipeline only once
            # Using a smaller model for demonstration; for production, consider larger models
            # or fine-tune one for specific book structures.
            model_name = os.getenv("TEXT_CLASSIFIER_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
            print(f"[TextClassifier] Initializing with model: {model_name}")
            cls._instance.classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
            )
            cls._instance.candidate_labels = [label for label in candidate_labels if label != ContentType.FALLBACK.value] # Remove fallback label
            print(f"[TextClassifier] Initialized with model: {model_name}")
        return cls._instance

    def classify_text(self, text: str) -> str:
        """
        Classifies a given text snippet into one of the predefined content types.
        Returns the top label. If classifier is not loaded, returns "paragraph_fallback".
        """
        if self.classifier is None:
            return ContentType.FALLBACK.value # Fallback if model loading failed

        text = text.strip()
        if not text:
            return ContentType.EMPTY.value
        
        print(f"[TextClassifier] Classifying text: '{text}'")

        # Limit text length for classification to avoid hitting model context limits
        # and improve inference speed. A typical headline is short.
        # For longer text, classification is likely "paragraph text".
        if len(text.split()) > 100: # Heuristic: if very long, it's likely a paragraph
            print(f"[TextClassifier] Text is too long, classifying as paragraph")
            return ContentType.PARAGRAPH.value

        try:
            results = self.classifier(text, self.candidate_labels, multi_label=False)
            # You can also return results['scores'][0] to analyze confidence
            print(f"[TextClassifier] Classified text: '{results['labels'][0]}'")
            return results['labels'][0]
        except Exception as e:
            print(f"Error during AI classification for text: '{text[:50]}...': {e}")
            return ContentType.FALLBACK.value # Fallback on error


# Singleton instance for efficient resource management
text_classifier = TextClassifier(
    candidate_labels=ContentType.get_all_values()
)