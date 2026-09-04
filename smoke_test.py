"""
Step 0 smoke test: prove Chatterbox can speak Russian in a cloned voice on this Mac,
and measure how long it actually takes.

Run:  .venv/bin/python smoke_test.py
"""

import time
import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

REFERENCE_WAV = "reference.wav"   # the voice to clone
RUSSIAN_TEXT = "Привет! Это тест клонирования голоса. Как у тебя дела сегодня?"

# MPS is Apple's GPU backend. Some operations aren't implemented for it yet,
# so this tells PyTorch to quietly run those few on the CPU instead of crashing.
import os
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"[1/3] Device: {device}")

# First run downloads several GB of model weights, then caches them for next time.
t0 = time.time()
model = ChatterboxMultilingualTTS.from_pretrained(device=device)
print(f"[2/3] Model loaded in {time.time() - t0:.1f}s")

# The actual test: generate Russian speech in the reference voice, and time it.
t0 = time.time()
wav = model.generate(
    RUSSIAN_TEXT,
    language_id="ru",
    audio_prompt_path=REFERENCE_WAV,
)
elapsed = time.time() - t0

audio_seconds = wav.shape[-1] / model.sr
ta.save("output_russian.wav", wav, model.sr)

print(f"[3/3] Generated {audio_seconds:.1f}s of audio in {elapsed:.1f}s")
print(f"      Real-time factor: {elapsed / audio_seconds:.2f}x "
      f"({'faster' if elapsed < audio_seconds else 'slower'} than real time)")
print("      Saved to output_russian.wav")
