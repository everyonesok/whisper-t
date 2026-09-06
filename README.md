# echo

Speak in English, hear it back in another language — **in your own voice**.

A learning prototype. Everything except the translation runs locally on your own machine, and no model is ever trained on your voice.

![status](https://img.shields.io/badge/status-prototype-orange) ![python](https://img.shields.io/badge/python-3.11-blue) ![platform](https://img.shields.io/badge/platform-Apple%20Silicon-lightgrey)

---

## How it works

Three stages chained together:

```mermaid
flowchart LR
    A[Your voice] --> B["Speech → text<br/>+ split into sentences<br/><i>faster-whisper</i><br/>local · ~1.4s"]
    B --> C["Translate<br/><i>Claude</i><br/>API · ~2.3s"]
    C --> D["Text → your voice<br/><i>Chatterbox</i><br/>local · ~11s"]
    D --> E[Cloned audio]
```

**Nothing is trained.** Chatterbox does *zero-shot* voice cloning: your reference recording is passed in as an input on every generation, the way you'd hand a reference image to an image model. The model weights never change and never learn anything about you. Swap `reference.wav` and the next sentence uses the new voice immediately.

**Why Claude for the middle step.** Speech recognition faithfully transcribes disfluencies, so the input to translation looks like *"um so I was I was thinking maybe we could meet on Tuesday instead"*. Claude is instructed to clean that up and translate idiomatically, producing *"Я тут подумал, может, встретимся лучше во вторник?"* rather than a literal rendering complete with the stutter.

---

## Requirements

- **macOS on Apple Silicon.** It runs on CPU elsewhere, but roughly 2× slower.
- **Python 3.11** (Chatterbox is developed and tested against it).
- **ffmpeg** — `brew install ffmpeg`.
- **An Anthropic API key.** Translation costs about **$0.0015 per sentence**, so $5 covers a few thousand.
- About **3GB of disk** for model weights, downloaded on first run.

---

## Setup

```bash
git clone <this repo> && cd whisper-t

# Python 3.11 environment
uv venv --python 3.11 .venv          # or: python3.11 -m venv .venv
VIRTUAL_ENV=.venv uv pip install -r requirements.txt

# Your API key
cp .env.example .env                  # then paste your key into .env
.venv/bin/python check_key.py         # verifies it works, without printing it
```

### Record your reference voice

The clone is only as good as this clip, and **recording level matters more than microphone quality**. A phone voice memo at a healthy level beats a laptop mic at a quiet one — in testing, a MacBook recording came in 20dB quieter than an iPhone one and cloned noticeably worse.

```bash
./record_voice.sh                     # 20s from the Mac mic, with a level check
./use_recording.sh ~/voice.m4a        # or convert anything you already have
```

Aim for 15–20 seconds of continuous, natural speech in a quiet room without echo. The words don't matter — nothing is being trained on them.

### Run it

```bash
.venv/bin/python server.py            # ~1 minute to load models, then open localhost:8000
```

Tap the microphone, speak, tap **Stop and translate**.

You can say several sentences. They're split at sentence boundaries and
played back one at a time, so you hear the first one while the rest are
still being generated.

---

## Performance

Measured on an M3 MacBook Air.

**One sentence** — about 15 seconds end to end:

| Stage | Time | Where |
|---|---|---|
| Speech → text | 1.4s | local (CPU) |
| Translate | 2.3s | Anthropic API |
| Voice generation | 11.4s | local (Apple GPU) |

**Several sentences** — each one is translated and spoken separately, so
playback starts long before the last one is finished:

| | First audio | All finished |
|---|---|---|
| one long clip (the old way) | 89.6s | 89.6s |
| sentence at a time | **21.6s** | 49.6s |

Chunking is 4.3x faster to first sound, and 1.8x faster overall — three
short generations beat one long one, because long inputs make the voice
model degrade (sampling slows from ~15 to ~1 tokens/sec and it can force
an early stop on repetition).

Voice generation is the bottleneck and it can't be parallelised: one
Chatterbox model on one GPU deadlocks if called from several threads, so
sentences queue. Translations do run concurrently, since they're just
network calls.

Recordings are capped at 30 seconds, and speech with no full stop is
broken at the last comma so a rambling sentence can't stall the queue.

The models are warmed up at startup with a throwaway generation, because
the first run after loading is roughly 4x slower than the rest.

## Limitations

- **Not real-time.** Tap, speak, tap, wait. Sentences arrive one at a time rather than all at the end, but simultaneous interpretation is a substantially harder problem.
- **Your accent is the model's, not yours.** Cross-lingual cloning transfers vocal timbre convincingly, but prosody comes from the model. It sounds recognisably like you speaking with a slight accent.
- **English input only.** `small.en` is English-only; switch `WHISPER_MODEL` in `pipeline.py` to `large-v3-turbo` for multilingual input at roughly 8× the transcription cost.
- **Russian stress marks are missing.** Chatterbox wants an optional `russian_text_stresser` package that isn't on PyPI, so stress placement is guessed. Occasionally audible — *кофе* can drift toward *кафе*.
- **Saving to a chosen folder needs Chrome or Edge.** It uses the File System Access API for a real save dialog; other browsers fall back to an ordinary download.

---

## Languages

All 22 target languages the voice model supports are enabled:

> Arabic · Chinese · Danish · Dutch · Finnish · French · German · Greek · Hebrew · Hindi · Italian · Japanese · Korean · Malay · Norwegian · Polish · Portuguese · Russian · Spanish · Swahili · Swedish · Turkish

**The voice model is the constraint, not the translation.** Claude translates into far more languages than this; Chatterbox can only *speak* these 23 (the 22 above plus English, the source).

Spot-checked end to end by translating, generating, then transcribing the audio back — Polish, Hindi, Arabic and Swedish all round-tripped accurately, so non-Latin scripts and right-to-left text are fine.

To change the list, edit `LANGUAGES` in `pipeline.py` — one line each. The key is the code Chatterbox knows, the value is the name Claude translates into:

```python
LANGUAGES = {
    "pl": "Polish",
}
```

To see every code the installed model accepts:

```bash
.venv/bin/python -c "from chatterbox.mtl_tts import SUPPORTED_LANGUAGES; print(SUPPORTED_LANGUAGES)"
```

---

## Layout

```
pipeline.py      The three stages. Loads models once, keeps them warm.
server.py        FastAPI. Streams a JSON event per sentence as each finishes.
index.html       The interface — one file, no build step.
check_key.py     Verifies your API key without printing it.
smoke_test.py    Proves voice cloning works before you build on it.
test_buffer.py   Unit tests for sentence chunking — no models, runs instantly.
bench_streaming.py  Measures chunked vs one-clip generation.
*.dc.html        Design source for the seven interface states.
canvas.json      Layout for those design artboards.
```

Progress in the UI is **real**, not a timer: the server emits an event as each stage and each sentence completes, and the page plays audio as it arrives.

---

## Two bugs worth knowing about

Both were found during development and are fixed here, but they're the kind that recur:

**Whisper invents words from silence.** Four seconds of silence and a pure 220Hz tone both transcribed as `"You"` — which would then be translated and spoken in your cloned voice as though you'd said it. Fixed by enabling voice-activity detection, which strips non-speech before transcription.

**A press that hides its own button never gets a release.** The mic button lived on a screen that gets hidden the moment recording starts, so `pointerup` bound to the button never fired and recording ran forever. Release is now watched on the window.

---

## Responsible use

**Only clone your own voice, or one you have explicit permission to use.**

Two things are worth knowing if you build on this:

**Everything generated here is watermarked.** Chatterbox applies Resemble AI's [Perth](https://github.com/resemble-ai/perth) imperceptible watermark to every clip before returning it. Audio produced by this tool can be identified as synthetic. Don't remove it.

**Your reference recording is personal data.** It stays on your machine — `.gitignore` excludes every audio format for exactly this reason — and it never leaves it, since the voice cloning runs locally. Only the translated *text* is sent anywhere.

---

## Licence & credits

Prototype code — do what you like with it.

Built on [Chatterbox](https://github.com/resemble-ai/chatterbox) (MIT, Resemble AI), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and the [Anthropic API](https://docs.anthropic.com).
