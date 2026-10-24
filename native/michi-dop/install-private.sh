#!/bin/sh
# M13 Gate A: install the evaluation plugin into an isolated prefix only.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
prefix=${1:-/tmp/michi-dop-gate-a}
mkdir -p "$prefix/lib/gstreamer-1.0"
plugin="$prefix/lib/gstreamer-1.0/libmichidop.so"
install -m 755 "$here/target/release/libmichidop.so" "$plugin"
sha=$(sha256sum "$plugin" | awk '{print $1}')
printf '{"name":"michidop","revision":"michidop-rust-0.1.0","sha256":"%s"}\n' \
    "$sha" > "$prefix/lib/gstreamer-1.0/michidop.manifest.json"
printf '%s\n' "$prefix"
