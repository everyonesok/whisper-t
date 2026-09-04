#!/bin/bash
# Turns any audio file into the reference voice the translator clones.
#
# Usage:  ./use_recording.sh ~/Downloads/my-recording.m4a
#
# Accepts whatever your phone or Mac produces — m4a, mp3, wav, aiff, caf —
# and converts it to the 24kHz mono WAV the model expects. The old reference
# is kept as reference_previous.wav so you can always go back.

set -e
cd "$(dirname "$0")"

SRC="$1"

if [ -z "$SRC" ]; then
  echo "Usage: ./use_recording.sh <audio file>"
  echo "Example: ./use_recording.sh ~/Downloads/voice.m4a"
  exit 1
fi

if [ ! -f "$SRC" ]; then
  echo "❌ Can't find: $SRC"
  exit 1
fi

echo "Source: $SRC"
ffprobe -i "$SRC" -show_entries stream=codec_name,sample_rate,channels,duration \
  -v quiet -of default=noprint_wrappers=1 | sed 's/^/  /'

DUR=$(ffprobe -i "$SRC" -show_entries format=duration -v quiet -of csv="p=0")
if (( $(echo "$DUR < 8" | bc -l) )); then
  echo "⚠️  Only ${DUR}s — aim for 15-20s of continuous speech for a good clone."
fi

if [ -f reference.wav ]; then
  cp reference.wav reference_previous.wav
  echo "Kept the old reference as reference_previous.wav"
fi

# -ar 24000 resamples, -ac 1 downmixes to mono. No volume processing:
# the clone is better off with your natural dynamics than a squashed signal.
ffmpeg -y -i "$SRC" -ar 24000 -ac 1 reference.wav -loglevel error

LEVELS=$(ffmpeg -i reference.wav -af volumedetect -f null /dev/null 2>&1)
MEAN=$(echo "$LEVELS" | grep mean_volume | sed 's/.*mean_volume: //')
MEAN_NUM=$(echo "$MEAN" | sed 's/ dB//')

echo ""
echo "✅ Wrote reference.wav (24kHz mono, mean $MEAN)"

if (( $(echo "$MEAN_NUM < -30" | bc -l) )); then
  echo "⚠️  That's quiet — healthy speech is around -25 to -15 dB."
  echo "   It'll work, but a louder recording will clone better."
fi

echo ""
echo "The next sentence you translate will use this voice — nothing to restart."
