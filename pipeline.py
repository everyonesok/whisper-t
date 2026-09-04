"""
The complete translate-in-your-voice pipeline, in one place.

Three stages:
    1. Speech  -> English text     (faster-whisper, local)
    2. English -> target language  (Claude, via the API)
    3. Text    -> your voice       (Chatterbox, local)

The models are loaded ONCE when you create a VoiceTranslator, then reused for
every request. That matters: loading takes ~50 seconds, generating takes ~10.
A web server creates one of these at startup and keeps it alive.

Run directly to test the whole thing on a file:
    .venv/bin/python pipeline.py reference.wav ru
"""

import os
import sys
import time

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
import torchaudio as ta
import anthropic
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

load_dotenv()

# Chatterbox identifies languages by these short codes; Claude needs the human
# name to translate into. Adding a language means adding one line here.
# Which speech-recognition model to use.
#
# "small.en" transcribes clean dictation as accurately as the much larger
# "large-v3-turbo" but roughly 8x faster (1.1s vs 9.6s on a 4-second clip),
# measured on this machine. Since speech-to-text was a third of the total
# wait, that's the single cheapest speedup available.
#
# Swap to "large-v3-turbo" if you hit accuracy trouble — heavy accents,
# background noise, or unusual vocabulary — or if you ever want to SPEAK
# a language other than English, since the ".en" models are English-only.
WHISPER_MODEL = "small.en"

# Every language the voice model can speak, minus English (the source).
#
# Two things have to agree for a language to work: the KEY must be a code
# Chatterbox knows (import SUPPORTED_LANGUAGES from chatterbox.mtl_tts to
# see them all), and the VALUE is the plain name Claude translates into.
# Adding a language really is one line — the constraint is the voice model,
# not the translation, since Claude handles far more languages than this.
LANGUAGES = {
    "ar": "Arabic",
    "zh": "Chinese",
    "da": "Danish",
    "nl": "Dutch",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "es": "Spanish",
    "sw": "Swahili",
    "sv": "Swedish",
    "tr": "Turkish",
}

TRANSLATION_SYSTEM = """You translate transcribed speech into {language}.

The input comes from speech recognition, so it may contain filler words, false
starts, and repetitions. Silently clean these up.

Translate the intended meaning naturally and idiomatically, the way a fluent
speaker would actually say it, rather than word for word.

Output ONLY the {language} translation. No explanation, no quotes, no preamble."""


class VoiceTranslator:
    def __init__(self, reference_voice="reference.wav"):
        self.reference_voice = reference_voice
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"

        print(f"Loading models (device={self.device})...", flush=True)
        t0 = time.time()

        # faster-whisper has no Apple GPU support, so it runs on CPU. It's the
        # quickest stage regardless, so this costs us very little.
        self.whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        self.tts = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
        self.claude = anthropic.Anthropic()

        print(f"Models loaded in {time.time()-t0:.1f}s", flush=True)

        # The very first generation is ~4x slower than the rest while the GPU
        # warms up. Burn that cost here at startup so the first real request
        # a user makes is fast, rather than making them wait 45 seconds.
        print("Warming up...", flush=True)
        t0 = time.time()
        self.tts.generate("Привет.", language_id="ru", audio_prompt_path=self.reference_voice)
        print(f"Warmed up in {time.time()-t0:.1f}s — ready.\n", flush=True)

    def transcribe(self, audio_path):
        """Stage 1: spoken audio -> written text."""
        # vad_filter strips non-speech BEFORE transcribing, which matters more
        # than it sounds: without it Whisper invents words out of nothing.
        # Four seconds of pure silence and a 220Hz tone both came back as
        # "You" — which would then be translated and spoken in your own
        # cloned voice as though you had actually said it.
        segments, info = self.whisper.transcribe(
            audio_path, beam_size=5, vad_filter=True
        )
        # Second guard: drop any segment the model itself thinks probably
        # isn't speech. Real speech scores about 0.02 here.
        kept = [s.text.strip() for s in segments if s.no_speech_prob < 0.8]
        return " ".join(kept).strip(), info.language

    def translate(self, text, lang_code):
        """Stage 2: text -> translated text, with speech disfluencies cleaned up."""
        language = LANGUAGES[lang_code]
        response = self.claude.messages.create(
            model="claude-opus-5",
            max_tokens=1000,
            system=TRANSLATION_SYSTEM.format(language=language),
            output_config={"effort": "low"},   # simple task; don't over-deliberate
            messages=[{"role": "user", "content": text}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"Translation refused: {response.stop_details}")

        # content is a list of typed blocks — find the text one rather than
        # assuming its position (thinking blocks come first on Opus 5).
        blocks = [b for b in response.content if b.type == "text"]
        if not blocks:
            raise RuntimeError(f"No text in response: {[b.type for b in response.content]}")
        return blocks[0].text.strip()

    def speak(self, text, lang_code, out_path="output.wav"):
        """Stage 3: translated text -> audio in the reference voice."""
        wav = self.tts.generate(
            text,
            language_id=lang_code,
            audio_prompt_path=self.reference_voice,
        )
        ta.save(out_path, wav, self.tts.sr)
        return out_path

    def run(self, audio_path, lang_code, out_path="output.wav"):
        """All three stages, with timings for each."""
        timings = {}

        t0 = time.time()
        transcript, detected = self.transcribe(audio_path)
        timings["transcribe"] = time.time() - t0

        t0 = time.time()
        translation = self.translate(transcript, lang_code)
        timings["translate"] = time.time() - t0

        t0 = time.time()
        self.speak(translation, lang_code, out_path)
        timings["speak"] = time.time() - t0

        return {
            "transcript": transcript,
            "detected_language": detected,
            "translation": translation,
            "audio_path": out_path,
            "timings": timings,
            "total": sum(timings.values()),
        }


if __name__ == "__main__":
    audio = sys.argv[1] if len(sys.argv) > 1 else "reference.wav"
    lang = sys.argv[2] if len(sys.argv) > 2 else "ru"

    translator = VoiceTranslator()
    result = translator.run(audio, lang, out_path="pipeline_output.wav")

    print(f"Heard:      {result['transcript']}")
    print(f"({LANGUAGES[lang]}): {result['translation']}")
    print()
    for stage, seconds in result["timings"].items():
        print(f"  {stage:<12} {seconds:5.1f}s")
    print(f"  {'TOTAL':<12} {result['total']:5.1f}s")
    print(f"\nSaved to {result['audio_path']}")
