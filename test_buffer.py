"""
Tests for SentenceBuffer — the chunking logic behind streaming.

No models, no API calls, runs in milliseconds. Pure text logic.

Run:  .venv/bin/python test_buffer.py
"""
from pipeline import SentenceBuffer

passed = failed = 0

def check(label, got, want):
    global passed, failed
    if got == want:
        print(f"  ✅ {label}")
        passed += 1
    else:
        print(f"  ❌ {label}")
        print(f"       got  {got}")
        print(f"       want {want}")
        failed += 1


print("\n── normal sentence chunking ──")

b = SentenceBuffer()
check("one complete sentence comes straight back",
      b.add("I went to the shop."),
      ["I went to the shop."])

b = SentenceBuffer()
check("several sentences at once all come back",
      b.add("First one. Second one. Third one?"),
      ["First one.", "Second one.", "Third one?"])

b = SentenceBuffer()
check("incomplete text is held, not emitted", b.add("Then I"), [])
check("...and completes when the rest arrives",
      b.add("walked home."), ["Then I walked home."])

b = SentenceBuffer()
b.add("A complete one. And the start of")
check("trailing fragment stays buffered", b.buffer, "And the start of")
check("flush returns the leftover", b.flush(), "And the start of")
check("buffer is empty after flush", b.buffer, "")
check("flush on empty buffer returns None", b.flush(), None)


print("\n── the safety valve ──")

# 26 words, no sentence ending, with commas — should cut at the LAST comma.
runon = ("so I went to the shop and then I picked up the parcel, "
         "and then I realised I had forgotten my wallet, so I had to walk back")
b = SentenceBuffer()
out = b.add(runon)
check("run-on emits a chunk rather than buffering forever", len(out), 1)
check("...and cuts at the last comma",
      out[0].endswith("forgotten my wallet,"), True)
check("...leaving the remainder buffered", b.buffer, "so I had to walk back")

# Under the soft limit — valve must NOT fire.
b = SentenceBuffer()
check("short text with a comma is NOT cut",
      b.add("The thing is, we are late"), [])

# Early comma only: cutting there would leave a stub, so it should wait.
b = SentenceBuffer()
stub = "Well, " + " ".join(f"word{i}" for i in range(1, 30))
out = b.add(stub)
check("early comma doesn't produce a 1-word stub",
      all(len(c.split()) >= 4 for c in out), True)

# No sentence ending AND no comma at all — hard limit must still cut.
b = SentenceBuffer()
out = b.add(" ".join(f"word{i}" for i in range(1, 51)))
check("no punctuation at all still gets cut", len(out) >= 1, True)
check("...at the hard limit of 40 words", len(out[0].split()), 40)


print("\n── incremental feeding, the way streaming will use it ──")

b = SentenceBuffer()
emitted = []
for piece in ["Could you send me", "the report by Friday?",
              "I also wanted", "to ask about the budget."]:
    emitted.extend(b.add(piece))
leftover = b.flush()
check("chunks assembled correctly across arrivals",
      emitted,
      ["Could you send me the report by Friday?",
       "I also wanted to ask about the budget."])
check("nothing left over", leftover, None)


print(f"\n{passed} passed, {failed} failed\n")
raise SystemExit(1 if failed else 0)
