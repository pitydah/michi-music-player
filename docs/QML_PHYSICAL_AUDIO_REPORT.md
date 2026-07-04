# QML Physical Audio Report

**Date:** 2026-07-04
**Status:** NO_VERIFICADO (requires `python main.py --qml` with display)

## Component Verification (offscreen)

| Component | Status | Notes |
|-----------|--------|-------|
| PlayerService | ✅ | GStreamerEngine + PlayerService created successfully |
| NowPlayingBridge | ✅ | Properties: trackTitle, trackArtist, position, duration |
| PlaybackBridge | ✅ | next(), previous() methods present |
| CoverBridge | ✅ | QML type registered |
| All 25 QML pages | ✅ | All route registry sources exist on disk |
| PlayerService.play() | ✅ | Method exists |
| PlayerService.pause() | ✅ | Method exists |
| PlayerService.seek() | ✅ | Method exists |
| PlayerService.set_volume() | ✅ | Method exists |
| PlayerService.stop() | ✅ | Method exists |

## Not Verified (requires runtime with display)

| Feature | How to Verify |
|---------|---------------|
| Play MP3 | `python main.py --qml`, click track in library |
| Play FLAC | Select FLAC file from library |
| Play WAV | Select WAV file from library |
| Cover display | Select track with embedded cover art |
| Placeholder cover | Select track without cover |
| Seek | Drag seek bar during playback |
| Play/Pause | Press space or click play button |
| Next/Prev | Click next/previous buttons |
| Volume | Drag volume slider |
| Mute | Click mute button |
| Shuffle | Toggle shuffle mode |
| Repeat | Toggle repeat mode |
| Queue | Open queue panel |
| Radio playback | Select radio station |

## Command to Verify
```bash
cd /home/cristian/music_player
python main.py --qml 2>&1 | tee /tmp/michi_qml_audio_test.log
```

Then check for errors:
```bash
grep -E "Failed to load|is not a type|Cannot assign|Binding loop|Cannot open|ReferenceError|TypeError|Traceback|Segmentation fault" /tmp/michi_qml_audio_test.log || echo "No errors found"
```
