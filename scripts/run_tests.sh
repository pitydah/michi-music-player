#!/bin/bash
# Run test files individually to avoid PySide6 multi-file crash.
# Usage: ./scripts/run_tests.sh [directory] [platform]
#   directory defaults to tests/qml/productive_workflows/
#   platform defaults to offscreen, use xcb for Xvfb
# Returns non-zero if any test file failed, crashed, or timed out.

DIR="${1:-tests/qml/productive_workflows}"
PLATFORM="${2:-offscreen}"
FAILED=0
CRASHED=0
TOTAL=0
PASSED=0
SKIPPED=0
TIMED_OUT=0

for f in "$DIR"/test_*.py; do
  if [ ! -f "$f" ]; then
    continue
  fi
  TOTAL=$((TOTAL + 1))
  name=$(basename "$f")
  echo ""
  echo "=== [$TOTAL] $name ==="
  junit_dir="${DIR}/results"
  mkdir -p "$junit_dir"
  junit_file="${junit_dir}/${name%.py}.xml"
  output=$(QT_QPA_PLATFORM=$PLATFORM timeout -s KILL 45 python -m pytest -p no:qt "$f" -q --tb=line --junitxml="$junit_file" 2>&1)
  rc=$?
  echo "$output" | tail -3
  if [ $rc -eq 0 ]; then
    PASSED=$((PASSED + 1))
  elif [ $rc -eq 5 ]; then
    SKIPPED=$((SKIPPED + 1))
    echo "  (no tests collected — empty file)"
  elif [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
    TIMED_OUT=$((TIMED_OUT + 1))
    echo "  TIMEOUT (exit code $rc)"
  elif [ $rc -eq 134 ]; then
    CRASHED=$((CRASHED + 1))
    echo "  CRASHED SIGABRT (exit code $rc)"
  elif [ $rc -eq 139 ]; then
    CRASHED=$((CRASHED + 1))
    echo "  CRASHED SIGSEGV (exit code $rc)"
  else
    FAILED=$((FAILED + 1))
    echo "  FAILED (exit code $rc)"
  fi
done

echo ""
echo "=========================================="
echo "Results: $TOTAL files | PASS=$PASSED FAIL=$FAILED CRASH=$CRASHED TIMEOUT=$TIMED_OUT SKIP=$SKIPPED"
echo "=========================================="
exit $((FAILED + CRASHED + TIMED_OUT))
