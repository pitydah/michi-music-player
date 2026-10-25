# michidop — M13 Gate A evaluation

Scoped, non-distributed Rust/GStreamer element approved only for M13 Gate A.
Gate B (release packaging, default discovery, production selection) is **NO-GO**.

## Contract

- Input: `audio/x-dsd, format=U8|DSDU8, layout=interleaved, channels=2`.
  For GStreamer `DSDU8`, rate is the DSD byte rate: 352800/705600/1411200 Hz.
- Output: `audio/x-raw, format=S24_3LE|S32LE, layout=interleaved, channels=2`,
  carrier rate = DSD byte rate / 2.
- Framing: two payload bytes per channel, marker `0x05`/`0xFA`, phase preserved
  across buffers.
- `reverse-payload-bits` reverses each input byte before packing.
- S32LE layout is LSB24 with one zero pad byte after each marker.
- `S32_MSB24`, DSD-to-PCM, DSP, volume, resampling and remixing are not implemented.

## Build and test

```sh
# Byte-reproducible release artifact: remap machine-specific paths.
RUSTFLAGS="--remap-path-prefix=$HOME/.cargo=/cargo --remap-path-prefix=$PWD/native/michi-dop=/michi" \
  cargo build --manifest-path native/michi-dop/Cargo.toml --release --locked
cargo test  --manifest-path native/michi-dop/Cargo.toml --release --locked
```

The corpus test reads the shared Python vectors in
`tests/dop/conformance/vectors/`. To prove installed discovery and bypass
in-process registration:

```sh
native/michi-dop/install-private.sh /tmp/michi-dop-gate-a
GST_PLUGIN_PATH=/tmp/michi-dop-gate-a/lib/gstreamer-1.0 \
MICHI_DOP_INSTALLED=1 \
cargo test --manifest-path native/michi-dop/Cargo.toml --release --test corpus
```

## Non-goals

No DSF demuxer, no host/session/playback wiring in this crate, no shipped
packaging, no production default. Those remain Gate B / AP2-F09 runtime work.
