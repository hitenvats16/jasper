from abc import ABC, abstractmethod
from pydantic import HttpUrl
import requests
from io import BytesIO
from clients.fal import FalSTSClient, FalModels, FalUtils
import io
import uuid
from typing import Dict, Any

class SpeechToSpeechStrategy(ABC):
    """Protocol for audio generation strategies."""

    @abstractmethod
    def transform(self, source_audio_buffer: io.BytesIO, target_audio_url: str, **kwargs) -> Dict[str, Any]:
        """Transform source audio to target audio."""
        ...

class ChatterboxSTS(SpeechToSpeechStrategy):
    """Strategy for generating audio using Chatterbox TTS model."""
    
    def __init__(self):
        self.client = FalSTSClient(
            model_name=FalModels.CHATTERBOX_STS.value
        )
    
    def transform(self, source_audio_buffer: io.BytesIO, target_audio_url: str, kwargs: dict = None) -> Dict[str, Any]:
        try:
            response = self.client.synthesize({
                "source_audio_url": FalUtils.upload_file(source_audio_buffer, kwargs.get("source_audio_file_name", f"{uuid.uuid4()}.mp3")),
                "target_audio_url": target_audio_url,
                "high_quality_audio": True,
            })
            
            if not response or 'url' not in response:
                print(f"[ChatterboxSTS] No valid response received: {response}")
                return None
                
            print(f"[ChatterboxSTS] Audio URL received: {response.get('url')}")
            
            # Download the audio from the URL
            audio_response = requests.get(response.get('url'))
            audio_response.raise_for_status()  # Raise an exception for bad status codes
            # Return the audio as a buffer
            audio_buffer = BytesIO(audio_response.content)
            print(f"[ChatterboxSTS] Downloaded audio size: {len(audio_response.content)} bytes")
            return {
                "audio_buffer": audio_buffer,
                "file_extension": response.get('url').split('.')[-1]
            }
            
        except Exception as e:
            print(f"[ChatterboxSTS] Error generating audio for chunk: {e}")
            import traceback
            traceback.print_exc()
            return None
