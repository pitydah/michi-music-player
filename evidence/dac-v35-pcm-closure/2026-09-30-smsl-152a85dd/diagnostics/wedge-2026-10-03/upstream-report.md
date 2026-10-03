# Upstream report draft — GStreamer state-change deadlock under rapid pipeline churn

Status: **ready to file** (gitlab.freedesktop.org/gstreamer/gstreamer issues).
The GitLab API/search is protected by Anubis, so this could not be matched
against existing issues automatically.

## Title
State-change deadlock: `gst_element_change_state` blocks forever on a pad
mutex held by a streaming thread under rapid playbin3+fakesink churn

## Environment
- GStreamer **1.28.7** (`libgstreamer-1.0.so.0.2807.0`, `libgstplayback`,
  `libgstcoreelements`), distributions: CachyOS (Arch-based), kernel
  7.2.8-1-cachyos, x86_64.
- Python 3.11 + PyGObject (GI) caller, but the deadlock is inside GStreamer
  C code (the Python frame is only the `set_state`/`get_state` call site).
- Media: local 12 s PCM WAV fixtures (44.1/48/96/192 kHz), decoded through
  `playbin3` with `fakesink` audio/video/text sinks (`sync=false`), isolated
  pipeline per characterization; also reproduced with a real `alsasink`
  pipeline (16-bit/48 kHz WAV) in a separate application path.

## Summary
Rapidly creating, prerolling (`set_state(PAUSED)`), querying
(`get_state(timeout)`) and destroying (`set_state(NULL)`) `playbin3`
pipelines occasionally **deadlocks permanently** inside the GStreamer state
machine. The blocked thread is inside `gst_element_change_state`
(recursing through libgstplayback) → `gst_pad_set_active` /
`gst_pad_activate_mode` / ghost-pad → `gst_pad_pause_task` →
`pthread_mutex_lock`, waiting on a pad mutex that a stuck streaming thread
(`typefind`/`wavparse`/`multiqueue`, all in `futex_wait`) never releases.
The bounded `get_state(5 s)` timeout does **not** recover: a sibling
pipeline call sits in `g_cond_wait_until` indefinitely.

## Reproduction
A directed stress harness (attached logic below) with two threads calling
characterization in a tight loop on the same fixtures and a second process
variant without any other pipeline activity reproduces the permanent
deadlock in **seconds to minutes**:

- 2 churn threads: stuck pipeline within ~11 s at ~300 pipelines/s.
- **1 churn thread: stuck pipeline within ~47 s** — so a single pipeline's
  own state transition can deadlock (not only cross-pipeline contention).
- An application-style `playbin3`+`alsasink` load/stop loop at ~7/s did not
  wedge within 8 min (3,485 cycles) but wedged after ~148k cycles in a long
  soak, i.e. the race is rare but scales with churn count.

Attached with this report: `stress.log`, `stacks-attempt1.log`,
`stacks-attempt2-pyspy.log`, `native-stacks.txt`,
`native.speedscope.json.gz` (py-spy native profile, 28,342 samples).

## Frozen native stack (leaf last)
```
characterize_local_file -> set_state(PAUSED)
pygi_function_cache_invoke -> pygi_invoke_c_callable -> ffi_call
libgstreamer gst_element_change_state (recursive, via libgstplayback)
gst_pad_set_active / gst_pad_activate_mode (ghost pad, multiqueue)
gst_pad_pause_task
pthread_mutex_lock -> libc __lll_lock_wait
```

## Impact
Any long-running process that churns pipelines (media players doing rapid
track changes or automated soak tests) can hang permanently with no
timeout-based recovery path. In our case an 8 h automated soak wedges twice
(148k and 189k pipeline lifecycles).

## Question
Is this a known race (e.g. pad task activation vs streaming thread holding
the pad lock) with a fix or workaround in a newer/older GStreamer, or should
this be investigated as a new issue? Crash/stack details and the
reproduction harness can be provided on request.
