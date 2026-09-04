"""
Does chunking actually get audio to the listener faster?

Measured on a 3-sentence recording (M3 MacBook Air):

    today, one long clip   ->  89.6s before anything plays
    chunked, serialised    ->  21.0s to first audio, 51.0s for all three

So 4.3x faster to first sound, and 1.8x faster overall -- three short
generations beat one long one outright, which matches the earlier
finding that long generations degrade (token repetition, sampling
slowing from ~15 it/s to ~1 it/s).

Voice generation is SERIALISED here deliberately.

The first attempt ran three generations as parallel threads against one
Chatterbox model and deadlocked outright -- CPU flat at 0%. One model on
one GPU cannot be shared that way. Translation is a network call so it
can overlap freely; voice generation has to queue.

Which is fine. The win was never "generate faster" -- it's "get the FIRST
chunk playable early", so playback starts while the rest still generates.
"""
import sys, time, os
sys.path.insert(0, "/Users/vlad/Documents/Claude/Projects/Translator")
os.chdir("/Users/vlad/Documents/Claude/Projects/Translator")
from concurrent.futures import ThreadPoolExecutor
from pipeline import VoiceTranslator

t = VoiceTranslator(reference_voice="reference.wav")
LANG = "ru"

start = time.time()
sentences = list(t.transcribe_chunks("reference.wav"))
print(f"  transcribe   {time.time()-start:5.1f}s → {len(sentences)} sentences")

# Translations run concurrently -- they're network calls, no shared model.
with ThreadPoolExecutor(max_workers=len(sentences)) as pool:
    translations = list(pool.map(lambda s: t.translate(s, LANG), sentences))
print(f"  translate    {time.time()-start:5.1f}s (all {len(sentences)}, in parallel)")

# Voice generation strictly one at a time.
first_playable = None
for i, ru in enumerate(translations, 1):
    t.speak(ru, LANG, f"/tmp/bench_chunk{i}.wav")
    at = time.time() - start
    if first_playable is None:
        first_playable = at
    print(f"  sentence {i} playable at {at:5.1f}s")

print(f"\n  FIRST AUDIO AT {first_playable:.1f}s   (all finished {time.time()-start:.1f}s)")
