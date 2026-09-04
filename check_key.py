"""
Checks that your Anthropic API key works, and tests the actual translation step.

This never prints your key. Run it after you've pasted the key into .env:

    .venv/bin/python check_key.py
"""

import os
import sys
from dotenv import load_dotenv
import anthropic

# Reads the .env file and puts its values into the environment,
# so os.environ can see them. The key never appears in this file.
load_dotenv()

key = os.environ.get("ANTHROPIC_API_KEY", "")

if not key or key == "paste-your-key-here":
    sys.exit("❌ No key found. Open .env and replace the placeholder with your real key.")

# Show just enough to confirm the right key loaded, without revealing it.
print(f"✅ Key loaded (ends with ...{key[-4:]}, {len(key)} characters)")

client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY automatically

# This is the real translation prompt the app will use. Two things matter here:
# 1. We tell it to clean up speech disfluencies ("um", false starts) that Whisper
#    faithfully transcribes but that you don't want spoken aloud in Russian.
# 2. We tell it to return ONLY the translation, so we can feed the result
#    straight into the voice model without stripping off any preamble.
SYSTEM = """You translate transcribed speech into Russian.

The input comes from speech recognition, so it may contain filler words, false
starts, and repetitions. Silently clean these up.

Translate the intended meaning naturally and idiomatically, the way a fluent
speaker would actually say it, rather than word for word.

Output ONLY the Russian translation. No explanation, no quotes, no preamble."""

test_input = "um so I was I was thinking maybe we could meet on Tuesday instead"

print(f"\nTranslating: {test_input!r}")

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=1000,
    system=SYSTEM,
    # "low" effort keeps Claude from deliberating at length over a task this
    # simple. It's faster and cheaper with no quality cost for translation.
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": test_input}],
)

# Always check stop_reason before reading content.
if response.stop_reason == "refusal":
    sys.exit(f"❌ Request refused: {response.stop_details}")

# response.content is a LIST of blocks, not a single answer. Because Opus 5
# thinks before replying, the first block is usually a ThinkingBlock and the
# actual answer sits in a TextBlock further along. Never assume content[0] is
# the text — always search for the block you want by its type.
text_blocks = [block for block in response.content if block.type == "text"]

if not text_blocks:
    sys.exit(f"❌ No text in response. Blocks were: {[b.type for b in response.content]}")

russian = text_blocks[0].text.strip()
print(f"Russian:     {russian!r}")

usage = response.usage
cost = (usage.input_tokens / 1_000_000 * 5) + (usage.output_tokens / 1_000_000 * 25)
print(f"\n✅ Working. Used {usage.input_tokens} input + {usage.output_tokens} output tokens.")
print(f"   Cost for this call: ${cost:.5f}  (~{int(16 / cost):,} more like it in your $16)")
