# ADR-0019: Translate for the ear: numbers as words

**Status:** Accepted
**Date:** 2026-10-02

## Context

The first native-speaker review of echo's Russian (2026-10-02) found the voice
natural and every stress correct, but the train time unclear: "Did you mean
14:07 or 14:05?" The translation had kept digits («Поезд прибывает 14-го в
7:45…»), so the voice model had to guess how to say them.

A round-trip check confirmed it. Spoken from digits, one take came out as
nonsense syllables and the other said the 13th instead of the 14th. For a
family app, a wrong date or time is the worst kind of error: it sounds
confident and sends someone to the wrong train.

## Decision

The translation instructions now say the text will be read aloud, so every
number, time and date is written out in words in the right grammatical form,
with no digits 0-9. Japanese and Chinese write numbers with characters.

## Consequences

- Measured: 24 translations of four number-heavy phrases in Russian, Japanese
  and Chinese contained no digits, and the Russian forms were correct
  («четырнадцатого», «второго марта»). Spoken in the cloned voice, all four
  test clips were transcribed back with the right date and time.
- The on-screen translation now shows numbers as words, which is longer and
  slower to scan than «7:45». The text is a script for the voice, not a
  written document.
- It's an instruction, not a guarantee. The first wording let one Japanese
  phrase keep digits; the firmer wording fixed it in testing, but a model
  could still slip. A code check for leftover digits would be the backstop
  if that shows up.
- It doesn't fix every number problem. One take still blurred «пять», and
  other things the voice reads poorly (abbreviations, symbols, foreign names)
  aren't covered yet.

## Alternatives considered

- **Keep digits and convert them in code** with a number-to-words library:
  Russian numbers change form with grammar (четырнадцать, четырнадцатого,
  четырнадцатому), and a converter doesn't know the sentence. The translator
  does.
- **Show digits on screen and speak words:** possible, and a real benefit:
  digits let the owner check numbers in a language they can't read. Deferred
  until the word form proves hard to use. If it's built:
  - **Don't convert words back to digits in code.** Number words also live
    inside ordinary phrases: Chinese 一点 ("a little") would become 1点
    ("1 o'clock"), Japanese 一緒 ("together") 1緒, Russian «сто лет не
    виделись» ("in ages") «100 лет». The converter would put the error on
    screen.
  - **Ask the translator for both versions in the same call**, one to show
    and one to speak, and check in code that both contain the same numbers.
    The screen is the owner's only check, so it must never disagree with the
    voice.
  - Anything timed or named from the text must use the spoken version: the
    result screen's sentence highlight estimates timing from text length.
    History and the saved filename need a deliberate choice.
  - The display text stays display-only and never drives the voice
    (ADR-0013).
- **Leave it to the voice model:** that's what produced the wrong date.
