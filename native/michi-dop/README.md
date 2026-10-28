# michidop — productive DoP GStreamer element

`michidop` is the Rust/GStreamer carrier packer selected by ADR 0012 and
implemented for AP2-F09. M13 Gate A (scoped native evaluation) and Gate B
(release packaging, installed discovery, production selection) were approved
on 2026-10-24. The crate is now part of the productive DoP vertical:

`PlaybackService → OutputSessionService → DopPlannerV3 → DopOutputExecutor →
supervised GStreamer host → michidop → selected ALSA endpoint`.

Python remains the independent conformance oracle; it is not the carrier
runtime.

## Contract

- Input: `audio/x-dsd, format=U8|DSDU8, layout=interleaved, channels=2`.
  For GStreamer `DSDU8`, rate is the DSD byte rate: 352800/705600/1411200 Hz.
- Output: `audio/x-raw, format=S24_3LE|S32LE, layout=interleaved, channels=2`,
  carrier rate = DSD byte rate / 2.
- Framing: two payload bytes per channel, marker `0x05`/`0xFA`, phase preserved
  across buffers, chunks and both channels.
- `reverse-payload-bits` reverses each input byte before packing.
- S32LE layout is LSB24 with one zero pad byte after each marker.
- `S32_MSB24`, DSD-to-PCM, DSP, volume, resampling and remixing are not
  implemented. A DoP carrier is never PCM musical content.

## Build and test

```sh
# Release artifact build: remap machine-specific paths (same-environment
# rebuilds are byte-identical; cross-environment equality is not claimed).
RUSTFLAGS="--remap-path-prefix=$HOME/.cargo=/cargo --remap-path-prefix=$PWD/native/michi-dop=/michi" \
  cargo build --manifest-path native/michi-dop/Cargo.toml --release --locked
strip --remove-section=.comment --remove-section=.note.gnu.build-id \
  native/michi-dop/target/release/libmichidop.so
cargo test  --manifest-path native/michi-dop/Cargo.toml --release --locked
```

Cross-environment byte identity is not claimed: the linker/GCC environment is
part of the build identity. `Cargo.lock` and the pinned Rust toolchain are
enforced, path remapping is applied, and a same-environment rebuild is
byte-identical. The release evidence records both local and CI SHA-256 values.

The corpus test reads the shared Python vectors in
`tests/dop/conformance/vectors/`. To prove installed discovery and bypass
in-process registration:

```sh
native/michi-dop/install-private.sh /tmp/michi-dop-gate-a
GST_PLUGIN_PATH=/tmp/michi-dop-gate-a/lib/gstreamer-1.0 \
MICHI_DOP_INSTALLED=1 \
cargo test --manifest-path native/michi-dop/Cargo.toml --release --test corpus
```

## Installed wheel

`MICHI_BUILD_DOP=1 python -m build --wheel` stages the plugin and manifest at
`<site-packages>/michi/native/gstreamer-1.0/`:

```text
libmichidop.so
michidop.manifest.json
```

`michi.infrastructure.audio_output.dop_plugin.resolve_dop_prefix()` resolves
that directory, or a Gate A root (`<root>/lib/gstreamer-1.0`), and fails closed
if the explicit prefix is incomplete. The host rejects a plugin whose manifest
or SHA-256 does not match. The installed-wheel end-to-end gate runs from
outside the checkout in a clean venv and requires a real `RUNNING` / EOS /
release sequence; a skip is a failure.

## Supervision and failure policy

The plugin never runs in the Qt owner process. The supervised host owns the
pipeline and exposes explicit `PREPARE_DOP` / `COMMIT_DOP` / `START_DOP` /
`PAUSE_DOP` / `RESUME_DOP` / `STOP_DOP` / `ABORT_DOP` / query operations.
Destructive operations bind plan, execution, stable device, binding locator and
generation, and host generation. A successful STOP or ABORT returns a release
receipt with those exact fields, terminal state `RELEASED` and provenance
`SUPERVISED_HOST`; a response is never treated as proof merely because it echoes
the caller's execution ID. The parent accepts a repeat STOP/ABORT only from a
receipt it retained for the exact execution and current host generation, and the
child can replay its retained receipt only after its pipeline and identity are
gone. Receipts are invalidated by a new prepare, host loss, supervisor restart,
identity loss or generation change, so receipt A can never certify execution B.
If release cannot be proven, the result is `DOP_RELEASE_UNCONFIRMED`; a lost
device remains logical `LOST`, the exact execution receipt stays pending, and no
resource is declared released on uncertainty.

## Scope

Included: productive DoP playback on a selected ALSA endpoint, installed
wheel discovery, conformance corpus, host integration and Signal Truth
lifecycle. Not included: AppImage/Flatpak/deb distribution, alternative DAC
formats without qualification and physical DAC DSD-mode verification (F14).

## Related AP2-F10 DSD→PCM path

The explicit DSD→PCM product route is a separate supervised pipeline built on
`DsdPolicyService`, `DsdToPcmPlanner` and `DsdPcmHostRuntime`; this Rust element
is never inserted into it. Conversion requires persisted, revisioned Settings
consent, exact F32LE/stereo cache qualification and a selected decoder. The
product route currently ends in the qualified PCM sink; the measured F06 PEQ
vertical is wired inside `DsdPcmHostRuntime` and remains lab-certified until
the product DSP transaction and numeric oracle are complete.
