#!/bin/bash
# Records your reference voice clip for the translator.
#
# Usage:  ./record_voice.sh
#
# Records 20 seconds from the MacBook microphone, saves it in the exact format
# Chatterbox wants (24kHz, mono), and checks it isn't too quiet or clipping.

set -e
cd "$(dirname "$0")"

DEVICE=":1"        # [1] MacBook Air Microphone — see: ffmpeg -f avfoundation -list_devices true -i ""
SECONDS_TO_RECORD=20
OUT="reference.wav"

# Keep the synthetic placeholder around so we can A/B against it later.
if [ -f "$OUT" ] && [ ! -f "reference_placeholder.wav" ]; then
  cp "$OUT" "reference_placeholder.wav"
  echo "Kept the old placeholder as reference_placeholder.wav"
fi

cat <<'PASSAGE'

────────────────────────────────────────────────────────────
Read this at your normal speaking pace. Don't perform it —
the point is to capture how you actually sound.

  I usually make coffee before anything else, then sit by
  the window and watch the street wake up. There's a bakery
  on the corner that opens early, and the smell reaches the
  flat by about eight. Some mornings I walk down and buy
  something warm, just to have a reason to leave the house.

If you'd rather just talk about your day for 20 seconds,
that works exactly as well. The words don't matter.
────────────────────────────────────────────────────────────

PASSAGE

for i in 3 2 1; do
  echo "  starting in $i..."
  sleep 1
done
echo "  ● RECORDING — ${SECONDS_TO_RECORD}s"

# -y overwrites, -t limits the duration, -ar/-ac set sample rate and mono.
if ! ffmpeg -y -f avfoundation -i "$DEVICE" -t "$SECONDS_TO_RECORD" \
     -ar 24000 -ac 1 "$OUT" -loglevel error 2>/tmp/rec_err.txt; then
  echo ""
  echo "❌ Recording failed. Most likely your terminal doesn't have microphone"
  echo "   permission yet. Open System Settings → Privacy & Security →"
  echo "   Microphone, switch on the app you're running this from, then retry."
  echo ""
  cat /tmp/rec_err.txt
  exit 1
fi

echo "  ■ stopped"
echo ""

# Quality check: a silent or clipped recording is the most common failure,
# and it produces a terrible clone rather than an obvious error.
LEVELS=$(ffmpeg -i "$OUT" -af volumedetect -f null /dev/null 2>&1)
MEAN=$(echo "$LEVELS" | grep mean_volume | sed 's/.*mean_volume: //')
MAX=$(echo "$LEVELS" | grep max_volume | sed 's/.*max_volume: //')
DUR=$(ffprobe -i "$OUT" -show_entries format=duration -v quiet -of csv="p=0")

echo "Saved $OUT — ${DUR}s, mean $MEAN, peak $MAX"

# Threshold note: a first attempt came in at -40 dB mean and sounded noticeably
# worse than a phone recording at -20 dB. Healthy speech sits around -25 to -15,
# so anything below -30 is worth re-recording rather than just flagging.
MEAN_NUM=$(echo "$MEAN" | sed 's/ dB//')
if (( $(echo "$MEAN_NUM < -30" | bc -l) )); then
  echo "⚠️  Too quiet ($MEAN). Healthy speech is around -25 to -15 dB."
  echo "   Sit closer, or record on your iPhone Voice Memos instead and drop"
  echo "   the .m4a in this folder — phone mics consistently come out louder."
elif (( $(echo "$MEAN_NUM > -10" | bc -l) )); then
  echo "⚠️  Very loud ($MEAN) and may be distorting — back off from the mic."
else
  echo "✅ Levels look good ($MEAN)."
fi

echo ""
echo "Playing it back..."
afplay "$OUT"
echo "Happy with it? If not, just run this again — it overwrites."
