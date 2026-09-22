#!/usr/bin/env bash
# demo.sh — see jeveloper work in one command.
#
#   export OPENROUTER_API_KEY=sk-or-...   # (or TYPESAFE_API_KEY); omit to see MOCK mode
#   ./demo.sh
#
# Runs a few real Jev decisions and prints the measured cost. No install needed.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
scripts="$here/skills/jeveloper/scripts"
JEVELOPER_METRICS="${JEVELOPER_METRICS:-${TMPDIR:-/tmp}/jeveloper-demo-$$.jsonl}"
export JEVELOPER_METRICS
rm -f "$JEVELOPER_METRICS" 2>/dev/null || true

if [ -z "${OPENROUTER_API_KEY:-}${TYPESAFE_API_KEY:-}" ]; then
  echo "⚠️  No Jev key set — running in MOCK mode (neutral placeholders)."
  echo "    export OPENROUTER_API_KEY=sk-or-...  to see real answers."
  echo
fi

run() { echo "▶ $1"; shift; python3 "$@"; echo; }

echo "=== jeveloper demo — Jev as the judge ==="
echo
run "Is a skipped test really a pass?  (expect a LOW number)" \
    "$scripts/jev_ask.py" noul "tests: 5 passed, 1 skipped" "All tests genuinely passed"
run "Which model for a mechanical 40-file rename?  (expect the cheap one)" \
    "$scripts/jev_ask.py" choice "Rename a symbol across 40 files, purely mechanical" \
    "Which model tier fits?" haiku:"cheap+fast" sonnet:"balanced" opus:"hardest reasoning"
run "Pick the next action for a flaky test" \
    "$scripts/jev_next.py" "Flaky test, fails 1 in 8, touches a shared cache" \
    "fix it without hiding a bug" add_retry:"retry 3x" fix_race:"fix the race" delete:"delete it"
run "Should this PR auto-merge?  (a decision tree)" \
    "$scripts/jev_tree.py" "$here/examples/decision-tree/auto-merge.json" \
    "PR adds CSV export. CI 8 passed, 0 skipped. No migrations. Touches only export module."

echo "=== what it cost / offloaded ==="
python3 "$scripts/jev_meter.py" report
rm -f "$JEVELOPER_METRICS"
