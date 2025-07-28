from abc import ABC, abstractmethod
from pydantic import HttpUrl
import requests
from io import BytesIO
from clients.fal import FalTTSClient, FalModels, FalSynthesisKwargs
from typing import Dict, Any

class AudioGenerationStrategy(ABC):
    """Protocol for audio generation strategies."""

    @abstractmethod
    def generate_audio(self, text: str, **kwargs) -> Dict[str, Any]:
        """Generate audio from text and return as buffer."""
        ...

class MinimaxAudioStrategy(AudioGenerationStrategy):
    """Strategy for generating audio using Chatterbox TTS model."""
    
    def __init__(self):
        self.client = FalTTSClient(
            model_name=FalModels.MINIMAX_SPEECH_02_HD_TTS.value
        )
    
    def generate_audio(self, 
                      text: str,
                      audio_generation_params: dict = None) -> Dict[str, Any]:
        try:
            response = self.client.synthesize(text, audio_generation_params)
            
            if not response or 'url' not in response:
                print(f"[MinimaxAudioStrategy] No valid response received: {response}")
                return None
                
            print(f"[MinimaxAudioStrategy] Audio URL received: {response.get('url')}")
            
            # Download the audio from the URL
            audio_response = requests.get(response.get('url'))
            audio_response.raise_for_status()  # Raise an exception for bad status codes
            # Return the audio as a buffer
            audio_buffer = BytesIO(audio_response.content)
            print(f"[MinimaxAudioStrategy] Downloaded audio size: {len(audio_response.content)} bytes")
            audio_buffer.seek(0)
            file_extension = response.get('url').split('.')[-1]
            return {
                "audio_buffer": audio_buffer,
                "file_extension": file_extension
            }
            
        except Exception as e:
            print(f"[MinimaxAudioStrategy] Error generating audio for chunk: {e}")
            import traceback
            traceback.print_exc()
            return None
