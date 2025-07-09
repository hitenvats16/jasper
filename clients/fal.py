from fal_client import InProgress 
import fal_client.client
from core.config import settings
from enum import Enum
from pydantic import BaseModel, HttpUrl

class FalModels(str, Enum):
    CHATTERBOX_TEXT_TO_SPEECH = "fal-ai/chatterbox/text-to-speech"

class FalSynthesisKwargs(BaseModel):
    audio_url: HttpUrl = None
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


class FalTTSClient:
    def __init__(self, model_name: FalModels = FalModels.CHATTERBOX_TEXT_TO_SPEECH):
        self.model_name = model_name
        self.client = fal_client.client.SyncClient(settings.FAL_API_KEY)

    def on_queue_update(self, update):
        if isinstance(update, InProgress):
            for log in update.logs:
                print("[FalTTSClient]",log["message"])

    def synthesize(self, text: str, kwargs: FalSynthesisKwargs = None) -> FalAudioResponse:
        print(f"[FalTTSClient] Synthesizing text: {text}")
        arguments = {"text": text}
        if kwargs:
            arguments.update(kwargs.model_dump())
        result = self.client.subscribe(
            self.model_name,
            arguments=arguments,
            with_logs=True,
            on_queue_update=self.on_queue_update,
        )
        print(result)
        return result.get("audio")