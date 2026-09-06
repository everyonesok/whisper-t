"""
The web server for the translator.

It does three jobs:
  1. Serves index.html (the interface)
  2. Loads the AI models ONCE at startup and keeps them in memory
  3. Runs the pipeline when the browser sends a recording

Start it with:  .venv/bin/python server.py
Then open:      http://localhost:8000

Startup takes about a minute — it loads two models and warms up the GPU.
Wait for "ready" before opening the page.
"""

import base64
import json
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import torch
import torchaudio as ta
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from pipeline import VoiceTranslator, LANGUAGES

HERE = Path(__file__).parent

# One translator for the whole server. Loading costs ~50 seconds, so it
# happens once at startup rather than per request.
translator: VoiceTranslator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global translator
    translator = VoiceTranslator(reference_voice=str(HERE / "reference.wav"))
    print("\n  ➜  Open http://localhost:8000\n")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


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


def join_wavs(paths, out_path):
    """
    Concatenate WAV files into one.

    Uses torchaudio rather than Python's built-in `wave` module, because
    the model writes 32-bit float WAVs (format tag 3) and `wave` only
    handles integer PCM — it raises "unknown format: 3" and leaves a
    zero-byte file behind.
    """
    audio = [ta.load(str(p)) for p in paths]
    sample_rate = audio[0][1]
    combined = torch.cat([wav for wav, _ in audio], dim=1)
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

        # ---- Stage 2: translate every sentence at once ----
        # These are independent network calls, so running them in parallel
        # costs nothing and gets all the text ready before the slow stage.
        t0 = time.time()
        try:
            with ThreadPoolExecutor(max_workers=min(len(sentences), 8)) as pool:
                translations = list(pool.map(
                    lambda s: translator.translate(s, language), sentences))
        except Exception as e:
            yield emit(stage="translate", status="error", message=str(e),
                       transcript=" ".join(sentences))
            return

        yield emit(stage="translate", status="done",
                   seconds=round(time.time() - t0, 1),
                   text=" ".join(translations))

        # ---- Stage 3: speak each sentence, in order ----
        # Emitting in order matters: the page plays chunks as they arrive,
        # so out-of-order delivery would scramble the sentences.
        yield emit(stage="speak", status="start", chunks=len(sentences))

        generated_paths = []          # kept so the clip can be saved to history

        for i, (source, translated) in enumerate(zip(sentences, translations), 1):
            t0 = time.time()
            try:
                out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                out.close()
                translator.speak(translated, language, out.name)
                wav_bytes = Path(out.name).read_bytes()
                generated_paths.append(out.name)
            except Exception as e:
                # One sentence failing shouldn't lose the others. Report it
                # and carry on -- the page can play what did work and show
                # the text for what didn't.
                yield emit(stage="chunk", index=i, total=len(sentences),
                           status="error", message=str(e),
                           source=source, text=translated)
                continue

            yield emit(stage="chunk", index=i, total=len(sentences),
                       status="done",
                       seconds=round(time.time() - t0, 1),
                       source=source, text=translated,
                       audio=base64.b64encode(wav_bytes).decode())

        total = round(time.time() - overall, 1)

        # Saving is best-effort: a full disk or a permissions problem
        # shouldn't lose a translation the user has already heard.
        saved = None
        try:
            saved = save_to_history(language, sentences, translations,
                                    generated_paths, total)
        except Exception as e:
            print(f"  could not save to history: {e}")

        yield emit(stage="complete", seconds=total,
                   saved=saved["id"] if saved else None)

    return StreamingResponse(run(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
