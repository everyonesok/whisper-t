"""
The complete translate-in-your-voice pipeline, in one place.

Three stages:
    1. Speech  -> English text     (faster-whisper, local)
    2. English -> target language  (Claude, via the API)
    3. Text    -> your voice       (Qwen3-TTS via Apple's MLX, local)

The models are loaded ONCE when you create a VoiceTranslator, then reused for
every request. Loading takes a few seconds once downloaded; generating a
sentence takes about two. A web server creates one of these at startup and
keeps it alive.

This branch runs Qwen3-TTS instead of Chatterbox — see ADR-0010. It needs
its own environment, .venv-mlx, because the two voice libraries require
incompatible versions of `transformers`.

Run directly to test the whole thing on a file:
    .venv-mlx/bin/python pipeline.py reference.wav ru
"""

import re
import sys
import time
from pathlib import Path

import anthropic
import numpy as np
import perth
import soundfile as sf
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from mlx_audio.tts.utils import load_model

load_dotenv()

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

# The voice model: Qwen3-TTS, "Base" variant (the one that can clone a voice;
# "CustomVoice" only has preset speakers), 1.7B parameters, weights stored at
# 6-bit precision. Measured on an M3: first sound after ~0.55s, 1.4x faster
# than realtime while streaming. The 0.6B version is faster (1.9x) but made
# more word errors in Russian. Apache-2.0, code and weights. ~2.7 GB download,
# fetched automatically on first run.
VOICE_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-6bit"

# Every language the voice model can speak, minus English (the source).
#
# The KEY is a short code used in URLs and history filenames. The VALUE does
# double duty: it's the name Claude translates into, and lowercased it's the
# language name Qwen3-TTS expects ("Russian" -> "russian"). Startup checks
# every one against the model, so a typo fails loudly instead of mid-sentence.
#
# Nine, down from Chatterbox's 22. Qwen3-TTS speaks ten languages including
# English. Lost in the switch: Arabic, Danish, Dutch, Finnish, Greek, Hebrew,
# Hindi, Malay, Norwegian, Polish, Swahili, Swedish and Turkish. They're still
# available on the main branch.
LANGUAGES = {
    "zh": "Chinese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
    "es": "Spanish",
}

TRANSLATION_SYSTEM = """You translate transcribed speech into {language}.

The input comes from speech recognition, so it may contain filler words, false
starts, and repetitions. Silently clean these up.

Translate the intended meaning naturally and idiomatically, the way a fluent
speaker would actually say it, rather than word for word.

Output ONLY the {language} translation. No explanation, no quotes, no preamble."""


# ── Chunking speech into translatable pieces ──────────────────────────
#
# Streaming needs the utterance broken into chunks so each one can run
# through translate-and-speak while you're still talking. The question is
# where to cut.
#
# What does NOT work (both tested and rejected):
#   - Whisper's own segment timestamps: it breaks roughly every 5 seconds
#     regardless of grammar, splitting "watch the street" / "wake up."
#   - Voice-activity detection pauses: identical boundaries to the above,
#     so VAD wasn't causing that split in the first place.
#   - Commas as a routine boundary: fragments lose context, drift in
#     register, and each generated clip gets its own rising-then-falling
#     intonation, so joined audio sounds like separate statements.
#
# What works: buffer the text and cut on sentence-ending punctuation,
# which Whisper transcribes reliably.

# Words we'll let accumulate without a sentence ending before forcing a
# break. ~25 words is roughly 8 seconds of speech. These limits were set
# when generation ran at 2.5x the audio length (Chatterbox) and a long
# chunk meant a 20-second wait; Qwen3-TTS makes that ~6 seconds, so they
# could now be relaxed. Left as-is to change one thing at a time.
CHUNK_SOFT_LIMIT_WORDS = 25

# Absolute ceiling, for speech with no sentence ending AND no comma.
# Breaking mid-clause is ugly, but an unbounded buffer is worse.
CHUNK_HARD_LIMIT_WORDS = 40

# Don't emit a chunk shorter than this. Prevents the safety valve from
# firing on an early comma and producing a 2-word fragment.
MIN_CHUNK_WORDS = 4

# A sentence ending is ./!/? optionally followed by a closing quote or
# bracket, and then whitespace or the end of the text. Requiring what
# follows stops it firing inside a decimal like "3.5".
_SENTENCE_END = re.compile(r'[.!?][")\]]?(?=\s|$)')


class SentenceBuffer:
    """
    Accumulates transcribed text and hands back chunks ready to translate.

    Feed it text as it arrives from transcription; it returns complete
    chunks when it has them, and holds onto anything incomplete. Call
    flush() when speech ends so trailing words are never dropped.

        buf = SentenceBuffer()
        buf.add("I went to the shop.")      -> ["I went to the shop."]
        buf.add("Then I")                   -> []          (incomplete)
        buf.add("walked home.")             -> ["Then I walked home."]

    The safety valve exists for run-on speech. A 12-second ramble with no
    full stop would otherwise be one huge chunk, meaning no pipelining and
    a full-length wait. Past the soft limit we cut at the last comma
    instead: a more audible seam, but a bounded wait.
    """

    def __init__(self,
                 soft_limit=CHUNK_SOFT_LIMIT_WORDS,
                 hard_limit=CHUNK_HARD_LIMIT_WORDS):
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.buffer = ""

    def add(self, text):
        """
        Add newly transcribed text. Returns a list of chunks now ready to
        translate — usually empty, sometimes one, occasionally several if
        multiple sentences arrived together.
        """
        self.buffer = (self.buffer + " " + text.strip()).strip()

        ready = []
        while True:
            chunk = self._take_one()
            if chunk is None:
                break
            ready.append(chunk)
        return ready

    def _take_one(self):
        """Pull one complete chunk off the front of the buffer, or None."""

        # Preferred cut: a real sentence ending.
        match = _SENTENCE_END.search(self.buffer)
        if match:
            cut = match.end()
            chunk = self.buffer[:cut].strip()
            self.buffer = self.buffer[cut:].strip()
            return chunk

        words = self.buffer.split()
        if len(words) < self.soft_limit:
            return None          # still short — wait for more speech

        # ── Safety valve ──────────────────────────────────────────────
        # No sentence ending, and we've waited long enough. Cut at the
        # LAST comma so the emitted chunk is as long as possible.
        comma = self.buffer.rfind(",")
        if comma != -1:
            candidate = self.buffer[:comma + 1].strip()
            # Only use it if the result isn't a stub. If the only comma is
            # near the start, cutting there gives a useless 2-word chunk
            # and leaves everything else behind, so keep waiting instead.
            if len(candidate.split()) >= MIN_CHUNK_WORDS:
                self.buffer = self.buffer[comma + 1:].strip()
                return candidate

        # No usable comma. Hold out until the hard ceiling, then cut
        # mid-clause rather than buffer forever.
        if len(words) >= self.hard_limit:
            chunk = " ".join(words[:self.hard_limit])
            self.buffer = " ".join(words[self.hard_limit:])
            return chunk

        return None

    def flush(self):
        """
        Call when speech has ended. Returns whatever is left — complete
        sentence or not — so the final words are never lost. Returns None
        if the buffer is empty.
        """
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining or None


class VoiceTranslator:
    def __init__(self, reference_voice="reference.wav"):
        self.reference_voice = reference_voice

        print("Loading models (voice on Apple GPU via MLX)...", flush=True)
        t0 = time.time()

        # faster-whisper has no Apple GPU support, so it runs on CPU. It's the
        # quickest stage regardless, so this costs us very little.
        self.whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        self.tts = load_model(VOICE_MODEL)
        self.claude = anthropic.Anthropic()

        # Chatterbox watermarked everything it generated, and the README
        # promises that. Qwen3-TTS doesn't, so we apply the same inaudible
        # Perth watermark ourselves. (Perth is Resemble AI's library, MIT,
        # separate from Chatterbox. It imports librosa, torch and others
        # without declaring them — see requirements.txt.)
        self.watermarker = perth.PerthImplicitWatermarker()

        print(f"Models loaded in {time.time()-t0:.1f}s", flush=True)

        # Fail at startup, not mid-translation, if a language in the list
        # isn't one this model actually speaks.
        supported = set(self.tts.get_supported_languages())
        missing = [name for name in LANGUAGES.values() if name.lower() not in supported]
        if missing:
            raise RuntimeError(f"Voice model doesn't support: {missing}")

        self.reference_text = self._reference_transcript()

        # The first generation compiles GPU kernels and is several times
        # slower. Burn that cost here so the first real request is fast.
        print("Warming up...", flush=True)
        t0 = time.time()
        self._generate("Привет.", "ru")
        print(f"Warmed up in {time.time()-t0:.1f}s — ready.\n", flush=True)

    def _reference_transcript(self):
        """
        Qwen3-TTS clones from the reference audio AND a transcript of it.
        Transcribe it once with Whisper and keep it next to the audio.

        Regenerated whenever reference.wav is newer than the transcript —
        otherwise re-recording your voice would silently keep the OLD
        words, and cloning would be quietly worse with no error.

        reference.txt is your own speech as text, so it's gitignored
        alongside the audio.
        """
        wav = Path(self.reference_voice)
        txt = wav.with_suffix(".txt")
        if txt.exists() and txt.stat().st_mtime >= wav.stat().st_mtime:
            return txt.read_text().strip()

        print("Transcribing reference voice (once)...", flush=True)
        text, _ = self.transcribe(str(wav))
        if not text:
            raise RuntimeError(f"Couldn't hear any speech in {wav}")
        txt.write_text(text)
        return text

    def _generate(self, text, lang_code):
        """
        Run Qwen3-TTS and return (samples, sample_rate), watermarked.

        stream=True even though the pieces are joined here: in mlx-audio
        streaming measured about twice as fast as whole-clip generation
        for the same sentence (1.4x vs 0.8x realtime).
        """
        pieces, sample_rate = [], None
        for result in self.tts.generate(
            text=text,
            ref_audio=self.reference_voice,
            ref_text=self.reference_text,
            lang_code=LANGUAGES[lang_code].lower(),
            stream=True,
            streaming_interval=0.32,
        ):
            pieces.append(np.array(result.audio, dtype=np.float32))
            sample_rate = result.sample_rate

        audio = np.concatenate(pieces)
        audio = self.watermarker.apply_watermark(audio, sample_rate=sample_rate)
        return audio.astype(np.float32), sample_rate

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

    def transcribe_chunks(self, audio_path):
        """
        Stage 1, streaming variant: yields complete sentences as they emerge.

        Same transcription as transcribe(), but instead of returning one
        blob of text at the end, it hands back each sentence the moment
        it's complete — so translation and voice generation for sentence
        one can start while sentence two is still being transcribed.

        This is a generator, so nothing runs until you iterate it:

            for sentence in t.transcribe_chunks("recording.wav"):
                ...          # runs once per sentence, as each is ready

        NOTE: this does NOT make transcription itself progressive.
        faster-whisper returns a generator, but the first next() does all
        the work — measured on a 17s file, all six segments became
        available at the same instant (2.35s), with or without VAD.
        Whisper processes audio in 30-second windows, so anything shorter
        is a single atomic forward pass with nothing to stream.

        The win is downstream: getting sentences as separate units lets
        translation and voice generation for sentence one start while
        two and three are still queued, instead of generating one long
        clip. For genuinely live streaming, the caller feeds successive
        audio slices in as they're recorded and SentenceBuffer stitches
        sentences across those calls.
        """
        segments, info = self.whisper.transcribe(
            audio_path, beam_size=5, vad_filter=True
        )

        buffer = SentenceBuffer()
        for segment in segments:
            # Same no-speech guard as transcribe() — drop anything the
            # model itself flags as probably not speech.
            if segment.no_speech_prob >= 0.8:
                continue
            for sentence in buffer.add(segment.text):
                yield sentence

        # Speech has ended. Whatever is left is a real (if unterminated)
        # thought — emit it rather than silently dropping the last words.
        leftover = buffer.flush()
        if leftover:
            yield leftover

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
        audio, sample_rate = self._generate(text, lang_code)
        # 32-bit float WAV, the same format Chatterbox wrote, so the history
        # joiner and the browser's WAV reader see nothing different.
        sf.write(out_path, audio, sample_rate, subtype="FLOAT")
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
