"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""

"""Smart mix controller — Daily, Unplayed, Popular, Favorites recent."""
import os

from sources.base_source import TrackRef


def _ctx_svc(win):
    return (
        getattr(getattr(win, "_services", None), "context_svc", None)
        or getattr(getattr(win, "_ctx", None), "context_svc", None)
    )


class SmartMixController:
    def __init__(self, window):
        self._win = window

    def _record_mix_opened(self, key: str, count: int):
        ctx = _ctx_svc(self._win)
        if not ctx:
            return
        ctx.update_selection(
            scope="mix",
            mix_key=key,
            album="",
            artist="",
            genre="",
            playlist_id=None,
            playlist_name="",
            folder_name="",
            search_query="",
        )
        ctx.record_mix_opened(key=key, count=count)

    def show_smart_mix(self, key):
        from library.smart_mixes import (get_daily_mix, get_unplayed,
                                        get_popular, get_favorites_recent)
        self._win._section_title.setText({
            "mix_daily": "Mix diario", "mix_unplayed": "No escuchadas",
            "mix_popular": "Más escuchadas",
            "mix_favorites": "Favoritos recientes",
        }.get(key, "Mix"))
        mixes = {"mix_daily": get_daily_mix, "mix_unplayed": get_unplayed,
                "mix_popular": get_popular, "mix_favorites": get_favorites_recent}
        fn = mixes.get(key)
        if not fn:
            self._win._views.show("empty")
            return
        files = fn()
        files = [f for f in files
                 if isinstance(f, str) and (f.startswith("http") or os.path.isfile(f))]
        refs = []
        if files:
            items = [self._win._items_index.get(f) for f in files]
            items = [i for i in items if i]
            refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                             artist=i.artist, album=i.album, duration=i.duration,
                             year=i.year, genre=i.genre) for i in items]
        self._win._model.populate(refs)
        self._win._current_refs = refs
        self._win._count.setText(f"{len(refs)} canciones")
        if refs:
            self._win._fade_content("library_hub")
            pc = getattr(self._win, "_playback_ctrl", None)
            if pc:
                pc.attach_track_table(self._win._table, self._win._model)
            else:
                self._win._table.setModel(self._win._model)
            self._win._table.setColumnWidth(0, 72)
            self._win._table.setColumnWidth(1, 260)
            self._win._table.setColumnWidth(2, 170)
            self._win._table.setColumnWidth(3, 170)
            self._win._table.setColumnWidth(4, 70)
            self._win._table.setColumnWidth(5, 130)
            self._win._table.setColumnWidth(6, 80)
            self._win._table.setColumnWidth(7, 260)
        else:
            self._win._views.show("empty")
        self._record_mix_opened(key, len(refs))

    def show_favs(self, key):
        favs = self._win._db.get_favorites()
        items = self.resolve_track_ids(favs)
        refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                         artist=i.artist, album=i.album, duration=i.duration,
                         year=i.year, genre=i.genre) for i in items]
        self._win._model.populate(refs)
        self._win._current_refs = refs
        self._win._count.setText(f"{len(refs)} canciones")
        if refs:
            self._win._fade_content("library_hub")
            pc = getattr(self._win, "_playback_ctrl", None)
            if pc:
                pc.attach_track_table(self._win._table, self._win._model)
            else:
                self._win._table.setModel(self._win._model)
            self._win._table.setColumnHidden(7, True)
            self._win._table.setColumnWidth(0, 72)
            self._win._table.setColumnWidth(1, 260)
            self._win._table.setColumnWidth(2, 170)
            self._win._table.setColumnWidth(3, 170)
            self._win._table.setColumnWidth(4, 55)
            self._win._table.setColumnWidth(5, 110)
            self._win._table.setColumnWidth(6, 75)
        else:
            self._win._views.show("empty")
        self._win._search.show()
        self._record_mix_opened("favs", len(refs))

    def show_recent(self, key):
        history = self._win._db.get_play_history()
        track_ids = [h.get("track_id", "") for h in history[:50] if h.get("track_id")]
        items = self.resolve_track_ids(track_ids)
        refs = [TrackRef(uri=i.filepath, title=i.title or os.path.basename(i.filepath),
                         artist=i.artist, album=i.album, duration=i.duration,
                         year=i.year, genre=i.genre) for i in items]
        self._win._model.populate(refs)
        self._win._current_refs = refs
        self._win._count.setText(f"{len(refs)} canciones")
        if refs:
            self._win._fade_content("library_hub")
            pc = getattr(self._win, "_playback_ctrl", None)
            if pc:
                pc.attach_track_table(self._win._table, self._win._model)
            else:
                self._win._table.setModel(self._win._model)
            self._win._table.setColumnHidden(7, True)
            self._win._table.setColumnWidth(0, 72)
            self._win._table.setColumnWidth(1, 260)
            self._win._table.setColumnWidth(2, 170)
            self._win._table.setColumnWidth(3, 170)
            self._win._table.setColumnWidth(4, 55)
            self._win._table.setColumnWidth(5, 110)
            self._win._table.setColumnWidth(6, 75)
        else:
            self._win._views.show("empty")
        self._win._search.show()
        self._record_mix_opened("recent", len(refs))

    def resolve_track_ids(self, track_ids: list) -> list:
        if not self._win._all_items and self._win._db:
            self._win._all_items = self._win._db.get_all()
            self._win._items_index = {i.filepath: i for i in self._win._all_items}
        id_map = {str(getattr(i, 'id', '')): i for i in self._win._all_items if getattr(i, 'id', None)}
        uid_map = {}
        for i in self._win._all_items:
            uid = getattr(i, 'track_uid', '')
            if uid:
                uid_map[str(uid)] = i
        results = []
        seen = set()
        for tid in track_ids:
            if tid in seen:
                continue
            item = self._win._items_index.get(tid) or id_map.get(tid) or uid_map.get(tid)
            if item is None:
                item = self._win._db.get_by_id(int(tid)) if tid.isdigit() else None
            if item:
                results.append(item)
                seen.add(tid)
        return results
