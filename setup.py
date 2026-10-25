"""Setuptools bridge for the optional Gate B native DoP artifact."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT / "native/michi-dop"


def _reproducible_rustflags() -> str:
    """Remap machine-specific paths so the native artifact is byte-stable.

    Cargo embeds registry and crate paths in panic location strings. Without a
    remap, a clean build from a different checkout produces a different
    libmichidop.so even with the same toolchain and Cargo.lock.
    """
    existing = os.environ.get("RUSTFLAGS", "").strip()
    if "--remap-path-prefix" in existing:
        return existing
    cargo_home = os.environ.get("CARGO_HOME") or str(Path.home() / ".cargo")
    remap = (
        f"--remap-path-prefix={cargo_home}=/cargo "
        f"--remap-path-prefix={NATIVE}=/michi"
    )
    return f"{existing} {remap}".strip()


class DopDistribution(Distribution):
    def has_ext_modules(self) -> bool:
        return os.environ.get("MICHI_BUILD_DOP") == "1"


class BuildPyWithDop(build_py):
    def run(self) -> None:
        super().run()
        if os.environ.get("MICHI_BUILD_DOP") != "1":
            return
        subprocess.run(
            ["cargo", "build", "--release", "--locked"],
            cwd=NATIVE,
            check=True,
            env={**os.environ, "RUSTFLAGS": _reproducible_rustflags()},
        )
        source = NATIVE / "target/release/libmichidop.so"
        if not source.is_file():
            raise RuntimeError(f"missing native DoP artifact: {source}")
        destination = Path(self.build_lib) / "michi/native/gstreamer-1.0"
        destination.mkdir(parents=True, exist_ok=True)
        plugin = destination / "libmichidop.so"
        shutil.copy2(source, plugin)
        digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
        manifest = {
            "name": "michidop",
            "revision": "michidop-rust-0.1.0",
            "sha256": digest,
            "rust_toolchain": "1.96.0",
            "gstreamer_abi": "1.28",
            "platform": "linux",
            "architecture": os.uname().machine,
            "build_options": ["--release", "--locked"],
        }
        (destination / "michidop.manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


setup(distclass=DopDistribution, cmdclass={"build_py": BuildPyWithDop})
