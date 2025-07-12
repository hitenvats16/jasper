import enum

class SilencingStrategies(str, enum.Enum):
    """Enum for different silencing strategies in audio generation."""
    
    FIXED_SILENCING = "fixed_silencing"
    ADAPTIVE_SILENCING = "adaptive_silencing"
    
    @classmethod
    def get_all_values(cls):
        """Get all enum values as a list."""
        return [strategy.value for strategy in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a value is a valid silencing strategy."""
        return value in cls.get_all_values() 