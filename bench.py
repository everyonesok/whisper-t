"""
Benchmark: is the 46s first generation just warmup, and is MPS actually helping?

Generates the same sentences repeatedly in ONE process (the way the real server
will, since it keeps the model loaded) so we can see steady-state speed rather
than cold-start speed.

Run:  .venv/bin/python bench.py mps
      .venv/bin/python bench.py cpu
"""

import os, sys, time
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

device = sys.argv[1] if len(sys.argv) > 1 else "mps"

SENTENCES = [
    "Привет, как дела?",
    "Я думаю, мы можем встретиться во вторник.",
    "Извините, я не говорю по-русски очень хорошо.",
]

t0 = time.time()
model = ChatterboxMultilingualTTS.from_pretrained(device=device)
print(f"device={device}  model load: {time.time()-t0:.1f}s", flush=True)

for run in range(2):
    for i, text in enumerate(SENTENCES):
        t0 = time.time()
        wav = model.generate(text, language_id="ru", audio_prompt_path="reference.wav")
        elapsed = time.time() - t0
        audio_s = wav.shape[-1] / model.sr
        print(f"  pass{run+1} s{i+1}: {elapsed:5.1f}s gen for {audio_s:4.1f}s audio "
              f"(RTF {elapsed/audio_s:.1f}x)", flush=True)
