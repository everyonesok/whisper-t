#!/bin/bash
# Fires when Claude stops. If source files changed but no ADR was added,
# says so.
#
# This exists because the discipline it enforces is exactly the kind that
# fails when it depends on remembering. A note in CLAUDE.md asking to
# "keep decisions updated" is advice; this is a check that runs whether or
# not anyone thought about it.
#
# It is a reminder, not a gate — it never blocks anything.

cd "$(dirname "$0")/../.." || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Files where a decision would actually live. Docs and tests are excluded:
# changing a test is not an architectural decision.
CHANGED=$(git status --porcelain -- '*.py' '*.html' '*.sh' 'requirements.txt' 2>/dev/null \
  | grep -vE 'test_|_test|/adr/' \
  | awk '{print $NF}')

[ -z "$CHANGED" ] && exit 0

# Did this session also add an ADR? Untracked or staged, either counts.
NEW_ADR=$(git status --porcelain -- 'docs/adr/*.md' 2>/dev/null \
  | grep -E '^\?\?|^A ' \
  | grep -vE 'README|template')

[ -n "$NEW_ADR" ] && exit 0

COUNT=$(echo "$CHANGED" | wc -l | tr -d ' ')
FILES=$(echo "$CHANGED" | head -4 | tr '\n' ' ')

# systemMessage surfaces to the user; additionalContext goes back to Claude
# so it can offer to write the record rather than the user having to ask.
cat <<JSON
{
  "systemMessage": "📋 $COUNT source file(s) changed, no ADR added: $FILES— if a decision was made, docs/adr/ is where it goes.",
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "Source files were modified this session ($FILES) with no new ADR in docs/adr/. If a genuine decision was made — one with a real alternative and a reason — offer to write one using docs/adr/template.md. If the change was routine (a fix, a rename, a tidy), say nothing."
  }
}
JSON
