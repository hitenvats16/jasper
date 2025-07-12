import numpy as np
import os
import io
from pydub import AudioSegment
from typing import List, Dict, Any, Optional
from scipy.io.wavfile import write as wav_write
from pydub.playback import play
from workers.audio_generation.silence import SilenceStrategy, AdaptiveSilenceStrategy
from workers.audio_generation.splitter import (
    TextSplittingStrategy,
    QuoteAwareTTSTextSplittingStrategy,
)
from workers.audio_generation.tts import (
    AudioGenerationStrategy,
    ChatterboxAudioStrategy,
)


class AudiobookGenerator:
    """Main audiobook generator using strategy patterns."""

    def __init__(
        self,
        audio_strategy: AudioGenerationStrategy,
        chunking_strategy: TextSplittingStrategy,
        silence_strategy: SilenceStrategy,
        output_sample_rate: int = 44100,  # Higher sample rate for better quality
        output_format: str = "wav",
    ):

        self.audio_strategy = audio_strategy
        self.chunking_strategy = chunking_strategy
        self.silence_strategy = silence_strategy
        self.output_sample_rate = output_sample_rate
        self.output_format = output_format.lower()

        if self.output_format not in ["wav", "mp3"]:
            raise ValueError("Unsupported output_format. Choose 'wav' or 'mp3'.")

        print(
            f"AudiobookGenerator initialized with:\n"
            f"  Audio Strategy: {type(audio_strategy).__name__}\n"
            f"  Chunking Strategy: {type(chunking_strategy).__name__}\n"
            f"  Silence Strategy: {type(silence_strategy).__name__}\n"
            f"  Output Sample Rate: {self.output_sample_rate}\n"
            f"  Output Format: {self.output_format.upper()}"
        )

    def generate(
        self,
        large_text: str,
        audio_gen_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[io.BytesIO]:
        """Generate a complete audiobook using the configured strategies.

        Returns:
            Optional[io.BytesIO]: The complete audio buffer if successful, None otherwise
        """
        print(
            f"\n✨ Starting audiobook generation for a text of {len(large_text)} characters ✨"
        )

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
            chunk_buffer = self.audio_strategy.generate_audio(
                chunk_text, audio_generation_params=audio_gen_params
            )
            print(
                f"[AudiobookGenerator] Generated audio for chunk #{i+1} out of {total_chunks}"
            )
            print(
                f"[AudiobookGenerator] Chunk buffer size: {chunk_buffer.getbuffer().nbytes} bytes"
            )

            if chunk_buffer and chunk_buffer.getbuffer().nbytes > 0:
                # Convert BytesIO buffer to numpy array for processing
                chunk_buffer.seek(0)

                # Load audio with proper format detection (don't assume wav)
                chunk_audio_segment = AudioSegment.from_file(chunk_buffer)

                # Get the original sample rate from the audio segment
                original_sample_rate = chunk_audio_segment.frame_rate
                print(
                    f"[AudiobookGenerator] Original audio sample rate: {original_sample_rate} Hz"
                )

                # Resample if necessary to match output sample rate
                if original_sample_rate != self.output_sample_rate:
                    print(
                        f"[AudiobookGenerator] Resampling from {original_sample_rate} Hz to {self.output_sample_rate} Hz"
                    )
                    chunk_audio_segment = chunk_audio_segment.set_frame_rate(
                        self.output_sample_rate
                    )

                # Convert to numpy array with proper normalization
                chunk_wav_data = np.array(
                    chunk_audio_segment.get_array_of_samples(), dtype=np.int16
                )

                # Add pause audio to the current chunk buffer
                if i < total_chunks - 1:  # Don't add silence after the very last chunk
                    # Use silence strategy
                    silence_ms = self.silence_strategy.get_silence_duration(
                        chunk_text, is_paragraph_end
                    )
                    print(f"  - Adding {silence_ms}ms silence to chunk buffer.")

                    silence_samples = int(silence_ms * self.output_sample_rate / 1000)
                    if silence_samples > 0:
                        silence_buffer = np.zeros(silence_samples, dtype=np.int16)
                        # Concatenate the chunk audio with silence
                        chunk_wav_data = np.concatenate(
                            [chunk_wav_data, silence_buffer]
                        )

                all_audio_arrays.append(chunk_wav_data)
                successful_chunks += 1

        if successful_chunks == 0:
            print("\n🚨 Warning: No audio was successfully generated.")
            return None

        print(
            f"\n[Stitching Complete] Concatenating all {successful_chunks} audio segments."
        )
        final_audio_data = np.concatenate(all_audio_arrays)
        print(
            f"Total audio duration (approx): {final_audio_data.size / self.output_sample_rate:.2f} seconds."
        )

        # Convert final audio data back to BytesIO buffer and return
        final_buffer = io.BytesIO()
        wav_write(final_buffer, self.output_sample_rate, final_audio_data)
        final_buffer.seek(0)

        return final_buffer


if __name__ == "__main__":
    audio_strategy = ChatterboxAudioStrategy()
    chunking_strategy = QuoteAwareTTSTextSplittingStrategy(max_tokens=30)
    silence_strategy = AdaptiveSilenceStrategy()
    audiobook_generator = AudiobookGenerator(
        audio_strategy, chunking_strategy, silence_strategy
    )
    text = """
        Akarçeşme is not a common surname. I have always liked it, though proper pronunciation outside 
        Türkiye has proved difficult. I did, however, come to regret that its uniqueness meant that members 
        of my family could be very easily identified once I had become a target of President Recep Tayyip Erdoğan. 
        For this reason, I do not name my siblings, who are currently in Türkiye, in this book. Retribution against 
        family members of those in disfavor with his government is not uncommon. It is only a small measure of protection, 
        but all I can provide.
        My mother’s family had lived in Giresun for generations, 
        but an unsubstantiated story asserts that their lineage traces 
        back to the family of a feudal lord named Karaosmanoğlu, which had 
        been exiled to the more isolated province from the more prosperous 
        western region of Türkiye. The Karaosmanoğlus were at one time one of 
        the most powerful families in Anatolia; however, they lost most of their 
        influence under the centralization and reform that took place during the reign of Mahmud II (1808-1839).
        Descendants now live in many areas, including Giresun, but while possible, 
        my own connection to this line is unconfirmed.
    """
    buffer = audiobook_generator.generate(
        text,
        "test.wav",
        {
            "audio_url": "https://pub-ac88a2c53a93464980d73555cf36e296.r2.dev/defaults/adam.wav"
        },
    )
    print(f"Audio saved to test.wav")
