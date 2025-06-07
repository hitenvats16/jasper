import logging

logger = logging.getLogger(__name__)

def generate_voice(text: str, output_dir: str = '.', speed: float = 1.0, device: str = 'auto', language: str = 'EN', accent: str = None, file_name: str = None):
    """
    Generate speech audio files for a specific accent (if provided) or multiple accents (if available) using the melo.api.TTS model.
    Args:
        text (str): The text to convert to speech.
        output_dir (str): Directory to save the output audio files.
        speed (float): Speed of the generated speech.
        device (str): Device to use for inference ('auto', 'cpu', 'cuda', etc.).
        language (str): Language code for the TTS model (e.g., 'EN', 'FR', etc.).
        accent (str, optional): Accent key to use (e.g., 'EN-US', 'EN-BR'). If None, generate all accents for English or default for other languages.
    """
    import os
    from melo.api import TTS

    model = TTS(language=language, device=device)
    speaker_ids = model.hps.data.spk2id
    
    if not file_name:
        file_name = text.lower().replace(" ", "_")

    if language.upper() == 'EN':
        accents = {
            'en-us': 'EN-US',
            'en-br': 'EN-BR',
            'en-india': 'EN_INDIA',
            'en-au': 'EN-AU',
            'en-default': 'EN-Default',
        }
        if accent:
            # Normalize accent key
            accent_key = accent.lower()
            if accent_key in accents:
                speaker_key = accents[accent_key]
                if speaker_key in speaker_ids:
                    output_path = os.path.join(output_dir, f"{accent_key}.wav")
                    model.tts_to_file(text, speaker_ids[speaker_key], output_path, speed=speed)
                    logger.info(f"Generated {output_path} for accent {speaker_key}")
                else:
                    logger.warning(f"Speaker key {speaker_key} not found for language {language}")
            else:
                logger.error(f"Accent '{accent}' not recognized. Available: {list(accents.keys())}")
        else:
            for file_suffix, speaker_key in accents.items():
                if speaker_key in speaker_ids:
                    output_path = os.path.join(output_dir, f"{file_suffix}.wav")
                    model.tts_to_file(text, speaker_ids[speaker_key], output_path, speed=speed)
                    logger.info(f"Generated {output_path} for accent {speaker_key}")
                else:
                    logger.warning(f"Speaker key {speaker_key} not found for language {language}")
    else:
        # For non-English, just use the first available speaker
        if speaker_ids:
            first_speaker = list(speaker_ids.values())[0]
            output_path = os.path.join(output_dir, f"{file_name.lower()}.wav")
            model.tts_to_file(text, first_speaker, output_path, speed=speed)
            logger.info(f"Generated {output_path} for language {language}")
        else:
            logger.error(f"No speakers found for language {language}")
            
            
            
generate_voice(
    '''
    Hello! This is a test of the text-to-speech system.

The quick brown fox jumps over the lazy dog.

Artificial intelligence is transforming the world at an incredible pace.

Can it handle questions? How about exclamations! Or even... pauses?

Let’s try numbers: one, ten, twenty-five, one hundred and one.

How about dates? Today is June 2nd, 2025. Tomorrow will be June 3rd.

Let’s test acronyms: NASA, AI, GPU, and HTML.

Emotional tone matters too. I'm so excited to see this working! But sometimes, I just feel tired.

Now for a tricky sentence: “She sells sea shells by the seashore.”

Another one: “The sixth sick sheik’s sixth sheep’s sick.”

Longer sentence for naturalness: Although the weather was gloomy, the little boy danced joyfully in the rain with his yellow umbrella.

Thanks for listening. That’s the end of the test.
'''
, output_dir="output", speed=1.0, device="auto", language="EN", accent="en-us", file_name="paritosh")