from fal_client import InProgress 
import fal_client.client
from core.config import settings
from enum import Enum
from pydantic import BaseModel, HttpUrl
from typing import Optional
import io
import uuid

class FalModels(str, Enum):
    MINIMAX_SPEECH_02_HD_TTS = "fal-ai/minimax/speech-02-hd"
    CHATTERBOX_STS = "resemble-ai/chatterboxhd/speech-to-speech"

class FalSynthesisKwargs(BaseModel):
    audio_url: Optional[str] = None
    exaggeration: float = 0.25
    temperature: float = 0.7
    cfg: float = 0.5

class FalAudioResponse(BaseModel):
    url: HttpUrl
    content_type: str
    file_name: str
    file_size: int

class FalSynthesizeResponse(BaseModel):
    audio: FalAudioResponse
    duration_ms: int # Duration of the audio in milliseconds

class FalUtils:
    @staticmethod
    def upload_file(file_buffer: io.BytesIO, file_name: str) -> str:
        file_path = f"temp_files/{uuid.uuid4()}_{uuid.uuid4()}_{file_name}.wav"
        with open(file_path, "wb") as f:
            f.write(file_buffer.getvalue())
        return fal_client.upload_file(file_path)

class FalTTSClient:
    def __init__(self, model_name: FalModels):
        self.model_name = model_name
        self.client = fal_client.client.SyncClient(settings.FAL_API_KEY)

    def on_queue_update(self, update):
        if isinstance(update, InProgress):
            for log in update.logs:
                print("[FalTTSClient]",log["message"])

    def synthesize(self, text: str, kwargs: dict) -> FalAudioResponse:
        print(f"[FalTTSClient] Synthesizing text: {text}")
        arguments = {"text": text}
        if kwargs:
            arguments.update(kwargs.model_dump())
        # Remove all keys from arguments where the value is None
        arguments = {k: v for k, v in arguments.items() if v is not None}
        result = self.client.subscribe(
            self.model_name,
            arguments=arguments,
            with_logs=True,
            on_queue_update=self.on_queue_update,
        )
        print(f"[FalTTSClient] {self.model_name}, Result: {result}")
        return result.get("audio")
    
class FalSTSClient:
    def __init__(self, model_name: FalModels):
        self.model_name = model_name
        self.client = fal_client.client.SyncClient(settings.FAL_API_KEY)

    def on_queue_update(self, update):
        if isinstance(update, InProgress):
            for log in update.logs:
                print("[FalSTSClient]",log["message"])
    
    def synthesize(self, kwargs: dict) -> FalAudioResponse:
        arguments = {}
        if kwargs:
            arguments.update(kwargs.model_dump())
        # Remove all keys from arguments where the value is None
        arguments = {k: v for k, v in arguments.items() if v is not None}
        result = self.client.subscribe(
            self.model_name,
            arguments=arguments,
            with_logs=True,
            on_queue_update=self.on_queue_update,
        )

        return result.get("audio")
