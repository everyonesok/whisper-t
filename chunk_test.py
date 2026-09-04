"""
Step 1 of the streaming plan: does VAD give us sentence-shaped chunks?

Nothing about the real app changes yet. This script takes one recording
of SEVERAL sentences and checks whether faster-whisper's voice-activity
detection naturally splits it at sentence boundaries -- which is the
assumption the whole streaming design rests on.

Run:  .venv/bin/python chunk_test.py <audio file>
"""
import sys
from faster_whisper import WhisperModel

audio_path = sys.argv[1] if len(sys.argv) > 1 else "reference.wav"

# small.en is what the live app uses -- same model, so timings are comparable.
model = WhisperModel("small.en", device="cpu", compute_type="int8")

# vad_filter=True is the exact setting that already fixed the silence-
# hallucination bug. Here we're asking a second question of the same
# feature: does it ALSO give us natural chunk boundaries?
segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)

print(f"Language: {info.language}\n")
for i, seg in enumerate(segments, 1):
    duration = seg.end - seg.start
    print(f"[chunk {i}]  {seg.start:5.1f}s → {seg.end:5.1f}s  "
          f"({duration:4.1f}s, no_speech={seg.no_speech_prob:.2f})")
    print(f"           {seg.text.strip()}")

print("\n--- merged into full sentences by punctuation ---")
model2 = WhisperModel("small.en", device="cpu", compute_type="int8")
segments2, _ = model2.transcribe(audio_path, beam_size=5, vad_filter=True)

buffer = ""
sentence_num = 1
for seg in segments2:
    buffer += (" " if buffer else "") + seg.text.strip()
    # A chunk is "ready" once the accumulated text ends in sentence-final
    # punctuation -- regardless of how many raw segments it took to get there.
    if buffer.rstrip().endswith((".", "?", "!")):
        print(f"[sentence {sentence_num}] {buffer.strip()}")
        sentence_num += 1
        buffer = ""

if buffer.strip():
    print(f"[incomplete, still buffering] {buffer.strip()}")
