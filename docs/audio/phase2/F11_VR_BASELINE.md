# F11 Visual Recovery — Baseline (S0)

Date: 2026-11-02
Reference HEAD: `84c7c3cde92795067015ff80f31226311aca0da0`
Phase: `AP2-F11 = ACTIVE`; F10 CLOSED; F12/F13/F14/F15 LOCKED; F14 NOT_RUN.
Spec: `docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md`
(spec sha256 `4f0e41eb6570527d40e2a40dff29e31214488efa8aed53d079320513122c6d12`).

This is a read-only baseline. It does not certify a new visual state.

## Verified starting point

- `git status --short`: only `?? .serena/`.
- F11 CI at the reference HEAD: runs `41375199479` (`7bd75a0`) and
  `41378465590` (`84c7c3c`) both 4/4 success.
- Existing F11 gate: 28 mandatory tests; the general suite documented
  6430 passed / 41 skipped before this sprint.
- Existing KWin captures in `evidence/f11/2026-11-01-f11-surfaces/` were
  produced with an empty library and no playback. They are layout evidence,
  not active-runtime evidence.

## KILLCRITIC findings mapped to code

| ID | Baseline location | Authority involved | New test / artifact |
|---|---|---|---|
| KX11-01 | `NowPlayingBar.qml::qualityBadge` green dot used `hasTrack` | Playback state vs Signal Truth | indicator bound to `SignalPathBridge.indicatorState` |
| KX11-02 | `MichiSignalNode.qml` used `root.y > 0` for the rail | presentation only | explicit `first`/`last`/`index`/`count` |
| KX11-03 | `unknown` rendered cyan | presentation only | closed status tokens + glyph + text |
| KX11-04 | fixed five stages; DSP/sample-rate summarized | `SignalTruthRecorder` | dynamic transformation stages |
| KX11-05 | chevron opened settings without disclosure | presentation intent | details first, configure second |
| KX11-06 | `SignalTruthPanel.qml` vs `SignalTruthPopup.qml` grammars | presentation only | one `MichiSignalPathView` renderer |
| KX11-07 | Advanced Graphic showed 31 dead chips | `GRAPHIC_EQ_NBANDS` not proven | compact limitation card |
| KX11-08 | sidebar rectangular blocks in compact/high-contrast captures | `MichiGlassSurface` backdrop source | recursive sidebar blur disabled; smoked material retained |
| KX11-09 | bridge used `active_snapshot or last_snapshot` | `SignalTruthRecorder` | ACTIVE / PENDING / HISTORICAL projection |
| KX11-10 | bootstrap rebuilt `F32LE` from library metadata | decoded runtime evidence | active snapshot decoded PCM only; otherwise fail closed |
| KX11-11 | Quick EQ `ON` reflected draft intent | `AudioProcessingBridge` | `stateLabel` distinguishes Draft/Applying/Effective/Bypassed/Error |
| KX11-12 | Advanced copied quick draft as committed filters | processing receipt | read-only current filters; no fake profile `Active` |
| KX11-13 | visual contract only hashed PNGs | QA | SHA manifest retained; active-scenario/pixel diff still pending |
| KX11-14 | popup min width could exceed tiny overlays | presentation geometry | viewport-safe min/max in F11 surfaces |
| KX11-15 | closure docs said CI missing while it was recorded | documentation | reconciled in this sprint |

## Exact authorities (no new owner)

- `SignalTruthRecorder`: canonical candidate/active/last evidence.
- `AudioProcessingService`: candidate/commit/readback/effective DSP.
- `OutputSessionService` + `AudioOutputBridge`: selected/pending/active route.
- `AudioTransportRouter` / hosted port: transport and host generations.
- `PlaybackService`: accepted media, position and transport intent.
- QML/bridges: presentation only; no DSP decisions.

## Baseline test commands

```text
python -m pytest tests/audio_phase2/test_f11_signal_path_bridge.py -q
python -m pytest tests/audio_phase2/test_f11_audio_processing_bridge.py -q
python -m pytest tests/test_f11_qml_contract.py -q
python -m pytest tests/test_qml_runtime_gate.py -q
```

## Baseline limitations

- No active-playback screenshots existed.
- No automated pixel/perceptual diff existed.
- Advanced Graphic/FIR/Profiles lacked a certified backend path.
- No physical DAC or bit-perfect claim is part of F11.
