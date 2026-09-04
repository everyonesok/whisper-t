"""
Tests the speech-to-text stage on the placeholder reference clip.

faster-whisper runs on the CPU on Mac (its engine has no Apple GPU support),
but it's small and quick enough that this isn't a problem — the voice cloning
stage dominates the total time anyway.

Run:  .venv/bin/python test_whisper.py
"""

import time
from faster_whisper import WhisperModel

# int8 keeps memory and CPU use low with very little accuracy cost.
t0 = time.time()
model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
print(f"Model loaded in {time.time()-t0:.1f}s")

t0 = time.time()
segments, info = model.transcribe("reference.wav", beam_size=5)
text = " ".join(segment.text.strip() for segment in segments)
elapsed = time.time() - t0

print(f"\nDetected language: {info.language} (confidence {info.language_probability:.2f})")
print(f"Transcribed {info.duration:.1f}s of audio in {elapsed:.1f}s")
print(f"\nText: {text}")
