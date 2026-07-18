from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from core.ai.model_catalog import ModelEntry, get_entry

logger = logging.getLogger("michi.model_manager")

_STORAGE_DIR = Path.home() / ".local" / "share" / "michi" / "models"
_STATUS_FILE = "status.json"
_AUTO_UNLOAD_MINUTES = 5

_MODEL_STATUS_VALUES = {
    "not_installed", "downloading", "verifying", "installed",
    "loading", "loaded", "unloading", "unloaded",
    "corrupt", "incompatible", "insufficient_memory",
}


class ModelManager:
    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self._storage = Path(storage_dir) if storage_dir else _STORAGE_DIR
        self._storage.mkdir(parents=True, exist_ok=True)
        self._loaded_models: dict[str, Any] = {}
        self._status: dict[str, str] = {}
        self._lock = threading.Lock()
        self._last_activity: dict[str, float] = {}
        self._auto_unload_minutes = _AUTO_UNLOAD_MINUTES
        self._load_status_file()
        self._start_auto_unload_timer()

    # ── Status ────────────────────────────────────────────────

    def get_status(self, model_id: str) -> str:
        if model_id in self._loaded_models:
            return "loaded"
        return self._status.get(model_id, "not_installed")

    def get_all_status(self) -> dict[str, str]:
        result = dict(self._status)
        for mid in self._loaded_models:
            result[mid] = "loaded"
        return result

    def is_installed(self, model_id: str) -> bool:
        status = self.get_status(model_id)
        return status in ("installed", "loaded", "unloaded")

    def is_loaded(self, model_id: str) -> bool:
        return model_id in self._loaded_models

    # ── Install / Download ────────────────────────────────────

    def install(self, model_id: str, progress_callback: Callable[[int, int], None] | None = None) -> bool:
        entry = get_entry(model_id)
        if entry is None:
            logger.error("Unknown model: %s", model_id)
            return False

        if self.is_installed(model_id):
            logger.info("Model %s already installed", model_id)
            return True

        dest_dir = self._storage / model_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / entry.gguf_file

        self._set_status(model_id, "downloading")
        try:
            self._download_file(entry.url, dest_path, progress_callback)
        except Exception as exc:
            logger.error("Download failed for %s: %s", model_id, exc)
            self._set_status(model_id, "corrupt")
            if dest_path.exists():
                dest_path.unlink()
            return False

        if entry.sha256:
            self._set_status(model_id, "verifying")
            if not self._verify_sha256(dest_path, entry.sha256):
                logger.error("SHA-256 mismatch for %s", model_id)
                self._set_status(model_id, "corrupt")
                dest_path.unlink()
                return False
        else:
            logger.info("No SHA-256 provided for %s, skipping verification", model_id)

        self._set_status(model_id, "installed")
        self._save_metadata(model_id, entry)
        logger.info("Model %s installed successfully (%d MB)", model_id, entry.size_mb)
        return True

    def delete(self, model_id: str) -> bool:
        self._unload(model_id)
        dest_dir = self._storage / model_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        self._status.pop(model_id, None)
        self._save_status_file()
        logger.info("Model %s deleted", model_id)
        return True

    def get_installed_models(self) -> list[str]:
        return [mid for mid, st in self.get_all_status().items() if st in ("installed", "loaded", "unloaded")]

    def get_storage_path(self) -> Path:
        return self._storage

    # ── Load / Unload from RAM ────────────────────────────────

    def load(self, model_id: str) -> Any:
        if model_id in self._loaded_models:
            self._touch_activity(model_id)
            return self._loaded_models[model_id]

        entry = get_entry(model_id)
        if entry is None:
            raise RuntimeError(f"Unknown model: {model_id}")

        gguf_path = self._storage / model_id / entry.gguf_file
        if not gguf_path.exists():
            self._set_status(model_id, "not_installed")
            raise RuntimeError(f"Model {model_id} not installed at {gguf_path}")

        self._set_status(model_id, "loading")
        try:
            import psutil
            mem = psutil.virtual_memory()
            needed_mb = entry.ram_estimate_mb
            if mem.available < needed_mb * 1024 * 1024:
                self._set_status(model_id, "insufficient_memory")
                raise RuntimeError(f"Insufficient memory: need {needed_mb}MB, have {mem.available / 1024 / 1024:.0f}MB")

            from llama_cpp import Llama

            cpu_count = os.cpu_count() or 2
            n_threads = max(1, cpu_count // 2)
            llm = Llama(
                model_path=str(gguf_path),
                n_ctx=2048,
                n_threads=n_threads,
                n_gpu_layers=0,
                verbose=False,
            )
            self._loaded_models[model_id] = llm
            self._touch_activity(model_id)
            self._set_status(model_id, "loaded")
            logger.info("Model %s loaded (%d MB RAM estimated)", model_id, entry.ram_estimate_mb)
            return llm
        except Exception as exc:
            self._set_status(model_id, "installed")
            raise RuntimeError(f"Failed to load {model_id}: {exc}") from exc

    def unload(self, model_id: str) -> None:
        self._unload(model_id)

    def unload_all(self) -> None:
        for mid in list(self._loaded_models.keys()):
            self._unload(mid)

    def _unload(self, model_id: str) -> None:
        if model_id not in self._loaded_models:
            return
        self._set_status(model_id, "unloading")
        try:
            del self._loaded_models[model_id]
            import gc
            gc.collect()
            self._set_status(model_id, "unloaded")
            logger.info("Model %s unloaded from RAM", model_id)
        except Exception as exc:
            logger.warning("Error unloading %s: %s", model_id, exc)
            self._set_status(model_id, "installed")

    def get_runtime_stats(self, model_id: str) -> dict[str, Any]:
        if model_id not in self._loaded_models:
            return {"loaded": False, "ram_mb": 0}
        try:
            import psutil
            proc = psutil.Process()
            ram = proc.memory_info().rss / (1024 * 1024)
        except Exception:
            ram = 0
        return {"loaded": True, "ram_mb": round(ram, 1)}

    # ── Internals ─────────────────────────────────────────────

    def _set_status(self, model_id: str, status: str) -> None:
        if status not in _MODEL_STATUS_VALUES:
            status = "not_installed"
        with self._lock:
            self._status[model_id] = status
        self._save_status_file()

    def _touch_activity(self, model_id: str) -> None:
        self._last_activity[model_id] = time.time()

    def _download_file(self, url: str, dest: Path, progress_callback: Callable[[int, int], None] | None = None) -> None:
        if not url:
            raise RuntimeError("No download URL available")

        response = urlopen(url, timeout=300)
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 8192

        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(downloaded, total)

        if total > 0 and downloaded != total:
            raise RuntimeError(f"Download incomplete: {downloaded}/{total} bytes")

    def _verify_sha256(self, path: Path, expected: str) -> bool:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest() == expected.lower()

    def _save_metadata(self, model_id: str, entry: ModelEntry) -> None:
        meta_path = self._storage / model_id / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump({
                "id": entry.id,
                "name": entry.name,
                "gguf_file": entry.gguf_file,
                "size_mb": entry.size_mb,
                "ram_estimate_mb": entry.ram_estimate_mb,
                "family": entry.family,
                "parameters": entry.parameters,
                "license": entry.license,
            }, f, indent=2)

    def _load_status_file(self) -> None:
        status_path = self._storage / _STATUS_FILE
        if status_path.exists():
            try:
                with open(status_path) as f:
                    self._status = json.load(f)
            except Exception:
                self._status = {}

    def _save_status_file(self) -> None:
        with self._lock:
            status_path = self._storage / _STATUS_FILE
            try:
                with open(status_path, "w") as f:
                    json.dump(self._status, f, indent=2)
            except Exception:
                pass

    def _start_auto_unload_timer(self) -> None:
        def _check():
            while True:
                time.sleep(60)
                now = time.time()
                for mid in list(self._loaded_models.keys()):
                    last = self._last_activity.get(mid, 0)
                    if now - last > self._auto_unload_minutes * 60:
                        logger.info("Auto-unloading %s after %d min of inactivity", mid, self._auto_unload_minutes)
                        self._unload(mid)

        t = threading.Thread(target=_check, daemon=True)
        t.start()
