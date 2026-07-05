#!/usr/bin/env bash
# QML Physical Audio Test — run with display
# Usage: bash scripts/qml_physical_audio_test.sh

set -euo pipefail

LOG="/tmp/michi_qml_audio_test.log"
PASSED=0
FAILED=0

pass() { PASSED=$((PASSED+1)); echo "  ✅ $1"; }
fail() { FAILED=$((FAILED+1)); echo "  ❌ $1"; }

echo "================================================"
echo "  Michi Music Player — QML Physical Audio Test"
echo "================================================"
echo ""

# ── 1. Start QML app ──
echo "--- Step 1: Start QML app ---"
cd /home/cristian/music_player
python main.py --qml > "$LOG" 2>&1 &
QML_PID=$!
sleep 5
if kill -0 $QML_PID 2>/dev/null; then
    pass "QML app started (PID $QML_PID)"
else
    fail "QML app failed to start"
    tail -20 "$LOG"
    exit 1
fi

# ── 2. Check log for errors ──
echo ""
echo "--- Step 2: Check startup errors ---"
ERRORS=$(grep -E "Failed to load|is not a type|Cannot assign|Binding loop|Cannot open|ReferenceError|TypeError|Traceback|Segmentation fault" "$LOG" || true)
if [ -z "$ERRORS" ]; then
    pass "No startup errors"
else
    fail "Startup errors found"
    echo "$ERRORS"
fi

# ── 3. Run route smoke test ──
echo ""
echo "--- Step 3: Route smoke test ---"
python scripts/smoke_ui_routes.py >> "$LOG" 2>&1 && pass "Route smoke passed" || fail "Route smoke failed"

# ── 4. Run QML pipeline tests ──
echo ""
echo "--- Step 4: QML test suite ---"
QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q >> "$LOG" 2>&1 && pass "All QML tests passed" || fail "Some QML tests failed"

# ── 5. Check audio output (manual) ──
echo ""
echo "--- Step 5: Audio playback (manual verification) ---"
echo ""
echo "  🎵 The app should be visible now."
echo "  Perform these checks manually:"
echo ""
echo "  [ ] Library loads (click 'Biblioteca' in sidebar)"
echo "  [ ] Click a track — audio plays through speakers"
echo "  [ ] Cover art visible (if track has embedded art)"
echo "  [ ] Placeholder shown for tracks without cover"
echo "  [ ] Pause (space or play button) — audio stops"
echo "  [ ] Resume — audio continues"
echo "  [ ] Seek (drag slider) — position changes"
echo "  [ ] Volume slider changes volume"
echo "  [ ] Mute button silences audio"
echo "  [ ] Next track — next song plays"
echo "  [ ] Previous track — previous song plays"
echo "  [ ] Shuffle toggle — order changes"
echo "  [ ] Repeat toggle — mode changes"
echo "  [ ] NowPlayingBar visible at bottom"
echo "  [ ] Click NowPlayingBar — ExpandedNowPlayingPanel opens"
echo "  [ ] Lyrics page — shows lyrics (if LRCLIB has them)"
echo "  [ ] Radio page — stations load (if network available)"
echo "  [ ] Radio station click — stream plays"
echo "  [ ] Settings page — tabs render"
echo "  [ ] EQ page — presets load, bypass works"
echo "  [ ] Queue — tracks listed"
echo "  [ ] Window resizes correctly (drag edge)"
echo ""

# ── 6. Kill QML app ──
echo "--- Step 6: Stop QML app ---"
kill $QML_PID 2>/dev/null || true
sleep 2
if ! kill -0 $QML_PID 2>/dev/null; then
    pass "QML app stopped cleanly"
else
    kill -9 $QML_PID 2>/dev/null || true
    fail "QML app had to be force-killed"
fi

# ── 7. Check for runtime errors ──
echo ""
echo "--- Step 7: Runtime errors ---"
RUNTIME_ERRORS=$(grep -E "Traceback|Segmentation fault|ERROR|CRITICAL" "$LOG" | grep -v "overrides\|Deprecation" || true)
if [ -z "$RUNTIME_ERRORS" ]; then
    pass "No runtime errors"
else
    echo "$RUNTIME_ERRORS"
    fail "Runtime errors found (see above)"
fi

# ── Summary ──
echo ""
echo "================================================"
echo "  Results"
echo "================================================"
echo "  Automated checks: $PASSED passed, $FAILED failed"
echo "  Manual checks: 21 (see step 5)"
echo "  Log: $LOG"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "  ✅ All automated checks passed."
    echo "  Manual checklist must be completed for VERIFIED status."
    exit 0
else
    echo "  ❌ Some automated checks failed."
    exit 1
fi
