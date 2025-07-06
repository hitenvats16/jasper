import torch
import numpy as np
import random
import os
from pydub import AudioSegment
from typing import List, Dict, Any, Optional, Tuple, Protocol
from scipy.io.wavfile import write as wav_write

from .silence import SilenceStrategy
from .splitter import TextSplittingStrategy
from .tts import AudioGenerationStrategy

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
        
class AudiobookGenerator:
    """Main audiobook generator using strategy patterns."""
    
    def __init__(self, 
                 audio_strategy: AudioGenerationStrategy,
                 chunking_strategy: TextSplittingStrategy,
                 silence_strategy: SilenceStrategy,
                 output_sample_rate: int = 24000,
                 output_format: str = "wav"):
        
        self.audio_strategy = audio_strategy
        self.chunking_strategy = chunking_strategy
        self.silence_strategy = silence_strategy
        self.output_sample_rate = output_sample_rate
        self.output_format = output_format.lower()
        
        if self.output_format not in ["wav", "mp3"]:
            raise ValueError("Unsupported output_format. Choose 'wav' or 'mp3'.")
        
        print(f"AudiobookGenerator initialized with:\n"
              f"  Audio Strategy: {type(audio_strategy).__name__}\n"
              f"  Chunking Strategy: {type(chunking_strategy).__name__}\n"
              f"  Silence Strategy: {type(silence_strategy).__name__}\n"
              f"  Output Sample Rate: {self.output_sample_rate}\n"
              f"  Output Format: {self.output_format.upper()}")

    def generate_audiobook(self,
                          large_text: str,
                          output_filepath: str,
                          audio_gen_params: Optional[Dict[str, Any]] = None,
                          preview_final_audio: bool = False):
        """Generate a complete audiobook using the configured strategies."""
        print(f"\n✨ Starting audiobook generation for a text of {len(large_text)} characters ✨")
        
        if audio_gen_params is None:
            audio_gen_params = {}

        # Use chunking strategy to split text
        text_chunks_with_metadata = self.chunking_strategy.chunk_text(large_text)
        total_chunks = len(text_chunks_with_metadata)
        print(f"Total chunks to process: {total_chunks}")

        all_audio_arrays = []
        successful_chunks = 0

        for i, (chunk_text, is_paragraph_end) in enumerate(text_chunks_with_metadata):
            # Use audio generation strategy
            print(f"[AudiobookGenerator] processing chunk #{i+1} out of {total_chunks}")
            print(f"[AudiobookGenerator] Transcribing text: \n {chunk_text}")
            chunk_wav_data = self.audio_strategy.generate_audio(chunk_text, **audio_gen_params)

            if chunk_wav_data.size > 0:
                all_audio_arrays.append(chunk_wav_data)
                successful_chunks += 1

                if i < total_chunks - 1:  # Don't add silence after the very last chunk
                    # Use silence strategy
                    silence_ms = self.silence_strategy.get_silence_duration(
                        chunk_text, is_paragraph_end
                    )
                    print(f"  - Adding {silence_ms}ms silence.")

                    silence_samples = int(silence_ms * self.output_sample_rate / 1000)
                    if silence_samples > 0:
                        all_audio_arrays.append(np.zeros(silence_samples, dtype=np.float32))

        if successful_chunks == 0:
            print("\n🚨 Warning: No audio was successfully generated.")
            return

        print(f"\n[Stitching Complete] Concatenating all {successful_chunks} audio segments.")
        final_audio_data = np.concatenate(all_audio_arrays)
        print(f"Total audio duration (approx): {final_audio_data.size / self.output_sample_rate:.2f} seconds.")

        # Export the final audiobook
        try:
            output_dir = os.path.dirname(output_filepath)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            wav_write(output_filepath, self.output_sample_rate, final_audio_data)
            print(f"\n🎉 Successfully generated audiobook to: {output_filepath}")
            print(f"  Final duration: {final_audio_data.size / self.output_sample_rate / 60:.2f} minutes.")

            if preview_final_audio:
                display(Audio(final_audio_data, rate=self.output_sample_rate))

        except Exception as e:
            print(f"\n❌ Error exporting final audio: {e}")
            print("Please ensure you have necessary codecs/backends installed.")