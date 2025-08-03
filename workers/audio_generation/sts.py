from abc import ABC, abstractmethod
from pydantic import HttpUrl
import requests
from io import BytesIO
from clients.fal import FalSTSClient, FalModels
import io
import uuid
from typing import Dict, Any
from utils.s3 import get_presigned_url, upload_file_to_s3
import time
import random

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
            model_name=FalModels.CHATTERBOX_STS_HD.value
        )
    
    def transform(self, source_audio_buffer: io.BytesIO, target_audio_url: str, kwargs: dict = None) -> Dict[str, Any]:
        max_retries = 5
        base_delay = 1  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                copy_buffer = io.BytesIO(source_audio_buffer.getvalue())
                copy_buffer.seek(0)
                print(f"[ChatterboxSTS] Attempt {attempt + 1}/{max_retries}")
                
                file_name = f"{uuid.uuid4()}_{kwargs.get('source_audio_file_name', f'{uuid.uuid4()}.mp3')}"
                temp_s3_key = f"transform_temp_files/{file_name}"
                upload_file_to_s3(copy_buffer, filename=file_name, custom_key=temp_s3_key)
                print(f"[ChatterboxSTS] payload:",{
                    "source_audio_url": get_presigned_url(temp_s3_key),
                    "target_voice_audio_url": target_audio_url,
                    "high_quality_audio": True,
                })
                response = self.client.synthesize({
                    "source_audio_url": get_presigned_url(temp_s3_key),
                    "target_voice_audio_url": target_audio_url,
                    "high_quality_audio": True,
                })
                print(f"[ChatterboxSTS] response: {response}")
                
                if not response or 'url' not in response:
                    print(f"[ChatterboxSTS] No valid response received: {response}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"[ChatterboxSTS] Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
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
                print(f"[ChatterboxSTS] Error on attempt {attempt + 1}: {e}")
                import traceback
                traceback.print_exc()
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[ChatterboxSTS] Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"[ChatterboxSTS] All {max_retries} attempts failed")
                    return None
