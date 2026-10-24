#!/bin/sh
# M13 Gate A: install the evaluation plugin into an isolated prefix only.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
prefix=${1:-/tmp/michi-dop-gate-a}
mkdir -p "$prefix/lib/gstreamer-1.0"
install -m 755 "$here/target/release/libmichidop.so" \
    "$prefix/lib/gstreamer-1.0/libmichidop.so"
printf '%s\n' "$prefix"
