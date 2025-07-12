from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime
from workers.audio_generation.enums import SilencingStrategies

class AdaptiveSilenceData(BaseModel):
    period: int
    comma: int
    paragraph: int
    default: int

class FixedSilenceData(BaseModel):
    value: int

class ConfigBase(BaseModel):
    tts_model: Optional[str] = None
    silence_strategy: Optional[str] = None
    silence_data: Optional[Union[AdaptiveSilenceData, FixedSilenceData, Dict[str, Any]]] = None
    tts_model_data: Optional[Dict[str, Any]] = None
    sample_rate: Optional[int] = None

    @field_validator('silence_strategy')
    @classmethod
    def validate_silence_strategy(cls, v):
        if v is not None and not SilencingStrategies.is_valid(v):
            raise ValueError(f"Invalid silence strategy: {v}. Valid options: {SilencingStrategies.get_all_values()}")
        return v

    @model_validator(mode='after')
    def validate_silence_data(self):
        if self.silence_data is not None and self.silence_strategy is not None:
            strategy = self.silence_strategy
            if strategy == SilencingStrategies.ADAPTIVE_SILENCING.value:
                if isinstance(self.silence_data, dict):
                    self.silence_data = AdaptiveSilenceData(**self.silence_data)
                elif not isinstance(self.silence_data, AdaptiveSilenceData):
                    raise ValueError("Adaptive silence strategy requires adaptive silence data format")
            elif strategy == SilencingStrategies.FIXED_SILENCING.value:
                if isinstance(self.silence_data, dict):
                    self.silence_data = FixedSilenceData(**self.silence_data)
                elif not isinstance(self.silence_data, FixedSilenceData):
                    raise ValueError("Fixed silence strategy requires fixed silence data format with 'value' field")
        return self

class ConfigCreate(ConfigBase):
    pass

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 