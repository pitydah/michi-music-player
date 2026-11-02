# F11 Visual Recovery — Performance

## Measured in this sprint

- Targeted F11/QML regression batch: 234 tests in 22.50 s (Qt offscreen).
- Full suite baseline at `cce711a`: 6430 passed / 41 skipped / 0 failed in
  2000.46 s.
- Productive DSP bridge test: 5 tests in 92.51 s including the real hosted
  GStreamer graph; signal processing itself is asynchronous.

## Not measured

- Popup open p95, drag frame rate and 256-point curve render p95 are NOT
  measured. No figure is invented.
- KWin compositor/GPU timing is not available in GitHub Actions.

## Design budget enforced

- No DSP compilation or IPC during slider drag; one commit per release/apply.
- Calculated response is cached by (rate, gains, preamp) and capped at 256
  points; no per-frame recomputation.
- No permanent animation in Signal Truth or the EQ response plot.
- Sidebar recursive blur is disabled to remove self-sampling work and artifact.
