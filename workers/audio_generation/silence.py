from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from .enums import SilencingStrategies

class SilenceStrategy(ABC):
    """Protocol for silence insertion strategies."""
    
    @abstractmethod
    def get_silence_duration(self, chunk_text: str, is_paragraph_end: bool, **kwargs) -> int:
        """Get silence duration in milliseconds for a chunk."""
        ...

class AdaptiveSilenceStrategy(SilenceStrategy):
    """Adaptive silence strategy based on punctuation and paragraph breaks.
    
    This strategy corresponds to SilencingStrategies.ADAPTIVE_SILENCING.
    """
    
    def __init__(self, silence_durations: Dict[str, int] = None):
        self.silence_durations = silence_durations or {
            "period": 700,    # Pause for end of sentence (., ?, !)
            "comma": 250,     # Pause for commas
            "paragraph": 1200, # Longer pause for new paragraphs
            "default": 150    # Short pause for other breaks
        }
    
    def get_silence_duration(self, chunk_text: str, is_paragraph_end: bool, **kwargs) -> int:
        """Get adaptive silence duration based on context."""
        if is_paragraph_end:
            return self.silence_durations.get("paragraph", 1200)
        elif chunk_text and chunk_text.strip()[-1] in ['.', '!', '?']:
            return self.silence_durations.get("period", 700)
        elif chunk_text and chunk_text.strip()[-1] == ',':
            return self.silence_durations.get("comma", 250)
        else:
            return self.silence_durations.get("default", 150)

class FixedSilenceStrategy(SilenceStrategy):
    """Fixed silence duration strategy.
    
    This strategy corresponds to SilencingStrategies.FIXED_SILENCING.
    """
    
    def __init__(self, silence_duration_ms: int = 200):
        self.silence_duration_ms = silence_duration_ms
    
    def get_silence_duration(self, chunk_text: str, is_paragraph_end: bool, **kwargs) -> int:
        """Return fixed silence duration."""
        return self.silence_duration_ms

def create_silence_strategy(strategy_type: str, data: dict) -> SilenceStrategy:
    """Factory function to create silence strategies based on the enum.
    
    Args:
        strategy_type: The type of silencing strategy to create (string value from SilencingStrategies enum)
        data: Configuration data for the strategy
        
    Returns:
        A configured SilenceStrategy instance
        
    Raises:
        ValueError: If an invalid strategy type is provided
    """
    if strategy_type == SilencingStrategies.FIXED_SILENCING.value:
        silence_duration = data.get('value', 200)
        return FixedSilenceStrategy(silence_duration_ms=silence_duration)
    
    elif strategy_type == SilencingStrategies.ADAPTIVE_SILENCING.value:
        return AdaptiveSilenceStrategy(silence_durations=data)
    
    else:
        raise ValueError(f"Invalid silencing strategy: {strategy_type}")