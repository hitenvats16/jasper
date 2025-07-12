from abc import ABC, abstractmethod
from pydantic import HttpUrl
import requests
from io import BytesIO
from clients.fal import FalTTSClient, FalModels, FalSynthesisKwargs

class AudioGenerationStrategy(ABC):
    """Protocol for audio generation strategies."""

    @abstractmethod
    def generate_audio(self, text: str, **kwargs) -> BytesIO:
        """Generate audio from text and return as buffer."""
        ...

class ChatterboxAudioStrategy(AudioGenerationStrategy):
    """Strategy for generating audio using Chatterbox TTS model."""
    
    def __init__(self, sample_rate: int = 44100):  # Higher sample rate for better quality
        self.sample_rate = sample_rate
        self.client = FalTTSClient(
            model_name=FalModels.CHATTERBOX_TEXT_TO_SPEECH.value
        )
    
    def generate_audio(self, 
                      text: str,
                      audio_generation_params: dict = None) -> BytesIO:
        try:
            # Use provided params or defaults optimized for quality
            params = audio_generation_params or {}
            exaggeration = params.get('exaggeration', 0.25)  # Lower for more natural speech
            temperature = params.get('temperature', 0.7)     # Balanced creativity
            cfg = params.get('cfg', 0.5)                    # Higher for more stable output
            seed = params.get('seed', None)
            audio_url = params.get('audio_url', None)
            
            print(f"[ChatterboxAudioStrategy] Generating audio with params: exaggeration={exaggeration}, temperature={temperature}, cfg={cfg}")
            
            response = self.client.synthesize(text, FalSynthesisKwargs(
                exaggeration=exaggeration,
                temperature=temperature,
                cfg=cfg,
                seed=seed,
                audio_url=audio_url
            ))
            
            if not response or 'url' not in response:
                print(f"[ChatterboxAudioStrategy] No valid response received: {response}")
                return None
                
            print(f"[ChatterboxAudioStrategy] Audio URL received: {response.get('url')}")
            
            # Download the audio from the URL
            audio_response = requests.get(response.get('url'))
            audio_response.raise_for_status()  # Raise an exception for bad status codes
            
            # Return the audio as a buffer
            audio_buffer = BytesIO(audio_response.content)
            print(f"[ChatterboxAudioStrategy] Downloaded audio size: {len(audio_response.content)} bytes")
            return audio_buffer
            
        except Exception as e:
            print(f"[ChatterboxAudioStrategy] Error generating audio for chunk: {e}")
            import traceback
            traceback.print_exc()
            return None
