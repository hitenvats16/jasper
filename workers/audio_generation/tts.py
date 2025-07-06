from chatterbox.tts import ChatterboxTTS
import torch
import numpy as np
import random
import os
from abc import ABC, abstractmethod

try:
    from IPython.display import Audio, display
except ImportError:
    print("IPython.display not found. Audio preview in notebook will not be available.")
    # Define dummy functions if not in IPython environment
    def Audio(data, rate):
        print("Audio playback unavailable (IPython.display not imported).")
        return None
    def display(obj):
        print(f"Display unavailable. Object type: {type(obj)}")

def set_seed(seed: int):
    """Sets the random seed for reproducibility."""
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)
    print(f"[Seed] Random seeds set to {seed}")

class AudioGenerationStrategy(ABC):
    """Protocol for audio generation strategies."""

    @abstractmethod
    def generate_audio(self, text: str, **kwargs) -> np.ndarray:
        """Generate audio from text and return as numpy array."""
        ...

class ChatterboxAudioStrategy(AudioGenerationStrategy):
    """Strategy for generating audio using Chatterbox TTS model."""
    
    def __init__(self, sample_rate: int = 24000):
        self.model = ChatterboxTTS.from_pretrained(device="cuda")
        self.sample_rate = sample_rate
        print(f"[ChatterboxAudioStrategy] Model loaded")
    
    def generate_audio(self, 
                      text: str,
                      exaggeration: float = 0.65,
                      temperature: float = 1,
                      seed_num: int = 45674,
                      cfgw: float = 0.1,
                      min_p: float = 0.05,
                      top_p: float = 1.0,
                      repetition_penalty: float = 1.2,
                      audio_prompt_path: str = None,
                      **kwargs) -> np.ndarray:
        """Generate audio using Chatterbox TTS."""
        if seed_num != 0:
            set_seed(int(seed_num))
        
        try:
            wav_data = self.model.generate(
                text,
                exaggeration=exaggeration,
                temperature=temperature,
                cfg_weight=cfgw,
                min_p=min_p,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                audio_prompt_path=audio_prompt_path
            )
            wav_data = wav_data.cpu().numpy()
            display(Audio(wav_data, rate=self.sample_rate))
            return wav_data.squeeze()
        except Exception as e:
            print(f"Error generating audio for chunk: {e}")
            # Return silence as fallback
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)  # 500ms silence
