from abc import ABC, abstractmethod
from pydantic import HttpUrl
import requests
from io import BytesIO
from clients.fal import FalTTSClient, FalModels, FalSynthesisKwargs
from typing import Dict, Any
import time
import random

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
        max_retries = 5
        base_delay = 1  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                print(f"[MinimaxAudioStrategy] Attempt {attempt + 1}/{max_retries}")
                
                response = self.client.synthesize(text, audio_generation_params)
                
                if not response or 'url' not in response:
                    print(f"[MinimaxAudioStrategy] No valid response received: {response}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[MinimaxAudioStrategy] Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
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
                print(f"[MinimaxAudioStrategy] Error on attempt {attempt + 1}: {e}")
                import traceback
                traceback.print_exc()
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[MinimaxAudioStrategy] Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"[MinimaxAudioStrategy] All {max_retries} attempts failed")
                    return None
