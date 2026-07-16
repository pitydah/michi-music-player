"""DevicesController — coordinates device scanning, storage views, and device navigation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.devices_ctrl")


class DevicesController:
    def __init__(self, window: MainWindow):
        self._win = window

    def show_device(self, key: str = ""):
        """Display device contents from a mount path."""
        w = self._win
        import os
        import shutil

        mount = key.split(":", 1)[1]
        usage = shutil.disk_usage(mount) if os.path.exists(mount) else None
        device_name = os.path.basename(mount)

        w._section_title.setText(device_name)
        w._section_subtitle.setText("Escaneando dispositivo...")
        w._count.setText("...")
        w._search.hide()
        w._fade_content("library_hub")

        w._model.populate([])
        if hasattr(w, '_playback_ctrl') and w._playback_ctrl:
            w._playback_ctrl.attach_track_table(w._table, w._model)
        else:
            w._table.setModel(w._model)

        from sources.base_source import TrackRef

        def _on_device_scanned(files: list[str]):
            if not hasattr(w, '_model') or w._current_section_key != "devices":
                return
            refs = [TrackRef(uri=fp, title=os.path.basename(fp), duration=0.0) for fp in files]
            w._model.populate(refs)
            w._current_refs = refs
            if usage:
                total_gb = usage.total / (1024**3)
                free_gb = usage.free / (1024**3)
                used_pct = (1 - usage.free / usage.total) * 100
                w._section_subtitle.setText(
                    f"{free_gb:.1f} GB libre de {total_gb:.1f} GB · "
                    f"{used_pct:.0f}% usado · {len(files)} canciones")
            else:
                w._section_subtitle.setText(f"{len(files)} canciones")
            w._count.setText(f"{len(files)} archivos")
            w._table.setColumnHidden(7, True)
            w._search.show()

        if w._workers:
            from library.devices import scan_device_music
            w._workers.run_task("device_scan", lambda: scan_device_music(mount),
                                on_done=_on_device_scanned)
        else:
            from library.devices import scan_device_music
            _on_device_scanned(scan_device_music(mount))
