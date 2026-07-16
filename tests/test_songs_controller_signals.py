"""Tests for SongsController Qt Signals."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestSongsControllerSignals:

    def test_controller_has_data_changed_signal(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        ctrl = SongsController(svc)
        assert hasattr(ctrl, 'data_changed')

    def test_controller_has_favorite_changed_signal(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        ctrl = SongsController(svc)
        assert hasattr(ctrl, 'favorite_changed')

    def test_controller_has_import_signals(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        ctrl = SongsController(svc)
        assert hasattr(ctrl, 'import_started')
        assert hasattr(ctrl, 'import_finished')

    def test_data_changed_emits_on_load(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        ctrl = SongsController(svc)
        received = []

        def handler(vs):
            received.append(vs)

        ctrl.data_changed.connect(handler)
        ctrl.load(items=[])
        assert len(received) == 1

    def test_data_changed_emits_on_apply_filter(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        from library.songs_view_state import SongsFilterState
        svc = MagicMock()
        svc.db = MagicMock()
        ctrl = SongsController(svc)
        ctrl.load(items=[])
        received = []

        def handler(vs):
            received.append(vs)

        ctrl.data_changed.connect(handler)
        ctrl.apply_filter(filter_state=SongsFilterState())
        assert len(received) >= 1

    def test_favorite_changed_emits_on_toggle(self):
        from legacy_widgets.ui.controllers.legacy_controllers.songs_controller import SongsController
        svc = MagicMock()
        svc.db = MagicMock()
        svc.db.toggle_favorite.return_value = True
        ctrl = SongsController(svc)
        ctrl.load(items=[])
        received = []

        def handler(tid, fav):
            received.append((tid, fav))

        ctrl.favorite_changed.connect(handler)
        item = MagicMock()
        item.filepath = "/m/s.flac"
        item.id = 42
        ctrl.toggle_favorite(item)
        assert len(received) == 1
        assert received[0] == (42, True)

    def test_premium_page_connects_data_changed(self):
        from ui.library.songs_premium_page import SongsPremiumPage
        ctrl = MagicMock()
        page = SongsPremiumPage()
        page.set_controller(ctrl)
        ctrl.data_changed.connect.assert_called_once()
