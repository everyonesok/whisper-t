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
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, Form
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

        for i, (source, translated) in enumerate(zip(sentences, translations), 1):
            t0 = time.time()
            try:
                out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                out.close()
                translator.speak(translated, language, out.name)
                wav_bytes = Path(out.name).read_bytes()
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

        yield emit(stage="complete", seconds=round(time.time() - overall, 1))

    return StreamingResponse(run(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
