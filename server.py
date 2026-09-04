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
        Yields one JSON object per line as each stage finishes, so the page
        can show real progress instead of guessing. This is why the three
        stages are called separately rather than via translator.run().
        """
        def emit(**payload):
            return json.dumps(payload) + "\n"

        try:
            wav_path = to_wav(raw)
        except subprocess.CalledProcessError:
            yield emit(stage="transcribe", status="error",
                       message="That recording couldn't be read.")
            return

        # ---- Stage 1: speech to text ----
        t0 = time.time()
        try:
            transcript, detected = translator.transcribe(wav_path)
        except Exception as e:
            yield emit(stage="transcribe", status="error", message=str(e))
            return

        if not transcript.strip():
            yield emit(stage="transcribe", status="error",
                       message="We didn't hear anything.")
            return

        yield emit(stage="transcribe", status="done",
                   seconds=round(time.time() - t0, 1),
                   text=transcript, detected=detected)

        # ---- Stage 2: translate ----
        t0 = time.time()
        try:
            translation = translator.translate(transcript, language)
        except Exception as e:
            yield emit(stage="translate", status="error", message=str(e),
                       transcript=transcript)
            return

        yield emit(stage="translate", status="done",
                   seconds=round(time.time() - t0, 1), text=translation)

        # ---- Stage 3: speak it in the cloned voice ----
        yield emit(stage="speak", status="start")
        t0 = time.time()
        try:
            out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            out.close()
            translator.speak(translation, language, out.name)
            wav_bytes = Path(out.name).read_bytes()
        except Exception as e:
            yield emit(stage="speak", status="error", message=str(e),
                       transcript=transcript, translation=translation)
            return

        # The audio rides back inside the JSON as base64 so the page gets
        # everything in one response — no second request to fetch it.
        yield emit(stage="speak", status="done",
                   seconds=round(time.time() - t0, 1),
                   audio=base64.b64encode(wav_bytes).decode())

    return StreamingResponse(run(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
