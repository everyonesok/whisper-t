"""
The web server for the translator.

It does three jobs:
  1. Serves index.html (the interface)
  2. Loads the AI models ONCE at startup and keeps them in memory
  3. Runs the pipeline when the browser sends a recording

Start it with:  .venv-mlx/bin/python server.py
Then open:      http://localhost:8000

Startup takes 10-20 seconds — it loads two models and warms up the GPU.
The very first run also downloads the voice model (~2.7 GB).
Wait for "ready" before opening the page.
"""

import base64
import json
import re
import subprocess
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio as ta
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from pipeline import VoiceTranslator, LANGUAGES

HERE = Path(__file__).parent

# One translator for the whole server. Loading costs 10-20 seconds, so it
# happens once at startup rather than per request.
translator: VoiceTranslator | None = None

# One voice model on one GPU must never run twice at once -- parallel
# generation deadlocked outright (ADR-0005). Within a request that's
# guaranteed by generating one stream; this lock covers two requests
# arriving together (two tabs, a double submit).
VOICE_LOCK = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global translator
    translator = VoiceTranslator(reference_voice=str(HERE / "reference.wav"))
    print("\n  ➜  Open http://localhost:8000\n")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def index():
    # Never let the browser reuse an old copy of the page. When the server's
    # event format changes (as it did for streaming, ADR-0012), a cached page
    # silently waits forever for events that no longer exist -- this bit
    # twice before this header existed.
    return FileResponse(HERE / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/languages")
def languages():
    return LANGUAGES


# ── Clip history ──────────────────────────────────────────────────────
#
# Every finished translation is written to history/ so you can come back
# and compare them — the same sentence in Japanese and Russian, say.
#
# The server does this rather than the browser because a web page can't
# read a folder from disk without a permission dance that breaks between
# sessions. The server is a local process with ordinary file access, so
# it just writes files and serves an index of them.
#
# Each clip is two files: <id>.wav (all sentences joined) and <id>.json
# (what you said, what it became, how long it took). Separate sidecars
# rather than one shared index file, so a write can't corrupt the lot.
HISTORY = HERE / "history"
HISTORY.mkdir(exist_ok=True)


# How much each sentence overlaps the next when clips are joined. Each
# sentence is generated separately, so each carries its own intonation —
# a rise at the start, a fall at the end. Butted together they sound like
# separate statements. A short crossfade blends the seam.
#
# 50ms is short enough to be inaudible as a fade and long enough to hide
# the discontinuity. Voicebox exposes 0–200ms as a slider; 50 is a sensible
# fixed default for speech.
CROSSFADE_MS = 50


def join_wavs(paths, out_path, crossfade_ms=CROSSFADE_MS):
    """
    Concatenate WAV files into one, crossfading each join.

    Uses torchaudio rather than Python's built-in `wave` module, because
    the model writes 32-bit float WAVs (format tag 3) and `wave` only
    handles integer PCM — it raises "unknown format: 3" and leaves a
    zero-byte file behind.

    The crossfade overlaps the last `crossfade_ms` of one clip with the
    first `crossfade_ms` of the next, fading one out as the other fades in.
    Total length shrinks by that much per join.
    """
    audio = [ta.load(str(p)) for p in paths]
    sample_rate = audio[0][1]
    fade = int(sample_rate * crossfade_ms / 1000)

    combined = audio[0][0]
    for wav, _ in audio[1:]:
        # Never fade more than either clip actually has.
        n = min(fade, combined.shape[1], wav.shape[1])
        if n <= 0:
            combined = torch.cat([combined, wav], dim=1)
            continue
        ramp = torch.linspace(0.0, 1.0, n)
        seam = combined[:, -n:] * (1.0 - ramp) + wav[:, :n] * ramp
        combined = torch.cat([combined[:, :-n], seam, wav[:, n:]], dim=1)

    ta.save(str(out_path), combined, sample_rate)
    return combined.shape[1] / sample_rate      # duration in seconds


def save_to_history(language, sentences, translations, wav_paths, total_seconds):
    """Write one finished translation into the history folder."""
    if not wav_paths:
        return None

    stamp = datetime.now()
    clip_id = f"{stamp:%Y%m%d-%H%M%S}-{language}"

    duration = round(join_wavs(wav_paths, HISTORY / f"{clip_id}.wav"), 1)

    meta = {
        "id": clip_id,
        "created": stamp.isoformat(timespec="seconds"),
        "language": language,
        "language_name": LANGUAGES.get(language, language),
        "source": " ".join(sentences),
        "translation": " ".join(translations),
        "sentences": len(sentences),
        "seconds": total_seconds,
        "duration": duration,
    }
    (HISTORY / f"{clip_id}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


@app.get("/api/history")
def history():
    """Every saved clip, newest first."""
    clips = []
    for meta_file in HISTORY.glob("*.json"):
        try:
            clips.append(json.loads(meta_file.read_text()))
        except (json.JSONDecodeError, OSError):
            continue          # a half-written file shouldn't break the list
    clips.sort(key=lambda c: c.get("created", ""), reverse=True)
    return clips


@app.get("/api/history/{clip_id}.wav")
def history_audio(clip_id: str):
    # Reject anything that isn't one of our own generated ids, so this
    # can't be talked into serving arbitrary files off the disk.
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-z]{2}", clip_id):
        raise HTTPException(status_code=404)
    path = HISTORY / f"{clip_id}.wav"
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="audio/wav")


@app.delete("/api/history/{clip_id}")
def history_delete(clip_id: str):
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-z]{2}", clip_id):
        raise HTTPException(status_code=404)
    removed = 0
    for suffix in (".wav", ".json"):
        path = HISTORY / f"{clip_id}{suffix}"
        if path.exists():
            path.unlink()
            removed += 1
    if not removed:
        raise HTTPException(status_code=404)
    return {"deleted": clip_id}


def to_wav(raw: bytes) -> str:
    """
    The browser records WebM/Opus. Convert it to a plain WAV that the
    speech recogniser can read, and return the temp file's path.
    """
    src = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    src.write(raw)
    src.close()

    dst = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    dst.close()

    subprocess.run(
        ["ffmpeg", "-y", "-i", src.name, "-ar", "16000", "-ac", "1",
         dst.name, "-loglevel", "error"],
        check=True,
    )
    return dst.name


@app.post("/api/translate")
async def translate(audio: UploadFile, language: str = Form("ru")):
    raw = await audio.read()

    def run():
        """
        Yields one JSON object per line as work completes.

        The recording is split into sentences, and each sentence makes its
        own trip through translate-and-speak. That means the FIRST sentence
        becomes playable while later ones are still generating -- measured
        at 21s instead of 90s for a three-sentence recording.

        Translations run concurrently (network calls, nothing shared).
        Voice generation strictly queues: one Chatterbox model on one GPU
        deadlocks if called from multiple threads at once.
        """
        def emit(**payload):
            return json.dumps(payload) + "\n"

        overall = time.time()

        try:
            wav_path = to_wav(raw)
        except subprocess.CalledProcessError:
            yield emit(stage="transcribe", status="error",
                       message="That recording couldn't be read.")
            return

        # ---- Stage 1: speech to sentences ----
        t0 = time.time()
        try:
            sentences = list(translator.transcribe_chunks(wav_path))
        except Exception as e:
            yield emit(stage="transcribe", status="error", message=str(e))
            return

        if not sentences:
            yield emit(stage="transcribe", status="error",
                       message="We didn't hear anything.")
            return

        yield emit(stage="transcribe", status="done",
                   seconds=round(time.time() - t0, 1),
                   text=" ".join(sentences),
                   chunks=len(sentences))

        # ---- Stage 2: translate the whole message ----
        # Two or more sentences go to the translator together, so it can
        # reorder or merge them the way a fluent speaker would (ADR-0020).
        # Rows come back in SPOKEN order, each with the English it covers.
        t0 = time.time()
        try:
            rows = translator.translate_message(sentences, language)
        except Exception as e:
            yield emit(stage="translate", status="error", message=str(e),
                       transcript=" ".join(sentences))
            return
        translations = [row["text"] for row in rows]   # in spoken order

        # The rows let the page show one row per spoken piece even though
        # the audio is a single stream.
        yield emit(stage="translate", status="done",
                   seconds=round(time.time() - t0, 1),
                   text=" ".join(translations),
                   sentences=rows)

        # ---- Stage 3: speak the whole message as ONE stream ----
        # Sentences were only split so each could be translated and shown on
        # its own row. The voice is generated in a single pass: separate
        # generations sounded like different speakers at every join
        # (ADR-0012). Streaming means the first sound still arrives in about
        # half a second, so the split no longer buys any speed.
        #
        # Each "audio" event is ~0.3s of raw 32-bit float PCM, little-endian,
        # base64-encoded, already watermarked. The page queues them for
        # gapless playback; nothing here waits for the whole clip.
        yield emit(stage="speak", status="start")
        t0 = time.time()
        pieces = []                       # kept so the clip can be saved to history
        sample_rate = None
        first_audio = None
        try:
            with VOICE_LOCK:
                for seq, (samples, sample_rate) in enumerate(
                        translator.speak_stream(" ".join(translations), language)):
                    if first_audio is None:
                        first_audio = round(time.time() - t0, 2)
                    pieces.append(samples)
                    yield emit(stage="audio", seq=seq, sample_rate=sample_rate,
                               samples=len(samples),
                               pcm=base64.b64encode(
                                   samples.astype("<f4").tobytes()).decode())
        except Exception as e:
            # The translation is still worth showing even if the voice failed.
            yield emit(stage="speak", status="error", message=str(e))
            return

        duration = sum(len(p) for p in pieces) / sample_rate if pieces else 0
        yield emit(stage="speak", status="done",
                   seconds=round(time.time() - t0, 1),
                   first_audio=first_audio,
                   duration=round(duration, 1))

        total = round(time.time() - overall, 1)

        # Save exactly what was streamed. Best-effort: a full disk or a
        # permissions problem shouldn't lose a translation already heard.
        saved = None
        try:
            if pieces:
                wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                wav.close()
                sf.write(wav.name, np.concatenate(pieces), sample_rate, subtype="FLOAT")
                saved = save_to_history(language, sentences, translations,
                                        [wav.name], total)
        except Exception as e:
            print(f"  could not save to history: {e}")

        yield emit(stage="complete", seconds=total,
                   saved=saved["id"] if saved else None)

    return StreamingResponse(run(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
