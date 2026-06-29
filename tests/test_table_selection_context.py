"""Tests: table selection without playback — _on_table_selection, proxy, detach, registry."""

from unittest.mock import MagicMock


class DummyTrackA:
    uri = "/music/song_a.flac"
    title = "Song A"
    artist = "Artist A"
    album = "Album A"
    genre = "Rock"
    duration = 180


class DummyTrackB:
    uri = "/music/song_b.flac"
    title = "Source Row 5"
    artist = "Artist B"
    album = "Album B"
    genre = "Jazz"
    duration = 200


class DummyModel:
    def __init__(self, track=None):
        self._track = track or DummyTrackA()

    def get_trackref(self, row):
        return self._track


class DummySourceModel:
    def get_trackref(self, row):
        if row == 5:
            return DummyTrackB()
        return DummyTrackA()


class DummySourceIndex:
    def row(self):
        return 5


class DummyProxyModel:
    def __init__(self, source=None):
        self._source = source or DummySourceModel()

    def sourceModel(self):
        return self._source

    def mapToSource(self, index):
        return DummySourceIndex()


class DummyInvalidSourceIndex:
    def isValid(self):
        return False

    def row(self):
        return 999


class DummyInvalidProxyModel:
    def sourceModel(self):
        return DummySourceModel()

    def mapToSource(self, index):
        return DummyInvalidSourceIndex()


class DummyExplodingModel:
    def get_trackref(self, row):
        raise IndexError("row out of range")


class DummyNoneModel:
    def get_trackref(self, row):
        return None


class DummyIndex:
    def __init__(self, row=0, model=None):
        self._row = row
        self._valid = True
        self._model = model

    def isValid(self):
        return self._valid

    def row(self):
        return self._row

    def model(self):
        return self._model


class TestTableSelectionContext:

    def test_on_table_selection_calls_update_selection(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl._on_table_selection(DummyIndex(), None)
        ctx_svc.update_selection.assert_called_once()
        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["scope"] == "track"
        assert kwargs["track"].title == "Song A"

    def test_does_nothing_if_index_invalid(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        idx = DummyIndex()
        idx._valid = False
        ctrl._on_table_selection(idx, None)
        ctx_svc.update_selection.assert_not_called()

    def test_does_nothing_if_no_model(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = None

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl._on_table_selection(DummyIndex(), None)
        ctx_svc.update_selection.assert_not_called()

    def test_attach_track_table_calls_setModel_and_connect(self):
        win = MagicMock()
        win._services = None
        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        model = MagicMock()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        result = ctrl.attach_track_table(table, model)
        assert result is table
        table.setModel.assert_called_once_with(model)
        sel.currentChanged.disconnect.assert_called_once()
        sel.currentChanged.connect.assert_called_once()

    def test_attach_track_table_registers_model_by_table(self):
        win = MagicMock()
        win._services = None
        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        model = MagicMock()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl.attach_track_table(table, model)
        assert ctrl._track_table_models[id(table)] is model

    def test_detach_track_table_removes_registry_entry(self):
        win = MagicMock()
        win._services = None
        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        model = MagicMock()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl.attach_track_table(table, model)
        assert id(table) in ctrl._track_table_models
        ctrl.detach_track_table(table)
        assert id(table) not in ctrl._track_table_models

    def test_detach_track_table_clears_active_table(self):
        win = MagicMock()
        win._services = None
        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        model = MagicMock()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl.attach_track_table(table, model)
        assert ctrl._active_context_table is table
        ctrl.detach_track_table(table)
        assert ctrl._active_context_table is None

    def test_connect_table_selection_disconnects_with_specific_slot(self):
        win = MagicMock()
        win._services = None
        win._ctx.table = MagicMock()
        sel = MagicMock()
        win._ctx.table.selectionModel.return_value = sel

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl.connect_table_selection(win._ctx.table)
        sel.currentChanged.disconnect.assert_called_once_with(
            ctrl._on_table_selection)
        sel.currentChanged.connect.assert_called_once_with(
            ctrl._on_table_selection)

    def test_connect_table_selection_does_not_play(self):
        win = MagicMock()
        win._services = None
        win._ctx.table = MagicMock()
        sel = MagicMock()
        win._ctx.table.selectionModel.return_value = sel
        win._ctx.model = DummyModel()
        win._ctx.context_svc = MagicMock()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        ctrl.connect_table_selection(win._ctx.table)
        signal_handler = sel.currentChanged.connect.call_args[0][0]
        signal_handler(DummyIndex(), None)

        win._ctx.playback.enqueue.assert_not_called()
        win._ctx.playback.play.assert_not_called()

    def test_on_selection_uses_current_model_before_global(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel(DummyTrackA())

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        local_model = DummyModel(DummyTrackB())
        idx = DummyIndex(model=local_model)
        ctrl._on_table_selection(idx, None)

        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["track"].title == "Source Row 5"

    def test_on_selection_fallback_to_registered_table_model(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel(DummyTrackA())

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        registered_model = DummyModel(DummyTrackB())
        ctrl.attach_track_table(table, registered_model)
        ctrl._active_context_table = table

        idx = DummyIndex(model=None)
        ctrl._on_table_selection(idx, None)

        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["track"].title == "Source Row 5"

    def test_on_selection_uses_proxy_source_model(self):
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel(DummyTrackA())

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        proxy = DummyProxyModel()
        idx = DummyIndex(model=proxy)
        ctrl._on_table_selection(idx, None)

        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["track"].title == "Source Row 5"

    def test_on_selection_proxy_uses_map_to_source_row(self):
        """If proxy row=0 maps to source row=5, context must use row 5."""
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyModel(DummyTrackA())

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        proxy = DummyProxyModel()
        idx = DummyIndex(row=0, model=proxy)
        ctrl._on_table_selection(idx, None)

        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["track"].title == "Source Row 5"

    def test_on_selection_invalid_proxy_falls_back(self):
        """Invalid source index should fall through to registry/global model."""
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = None

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        table = MagicMock()
        sel = MagicMock()
        table.selectionModel.return_value = sel
        ctrl.attach_track_table(table, DummyModel(DummyTrackB()))
        ctrl._active_context_table = table

        idx = DummyIndex(model=DummyInvalidProxyModel())
        ctrl._on_table_selection(idx, None)

        kwargs = ctx_svc.update_selection.call_args[1]
        assert kwargs["track"].title == "Source Row 5"

    def test_on_selection_exploding_model_does_not_crash(self):
        """get_trackref that raises should be caught."""
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyExplodingModel()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        idx = DummyIndex(model=DummyExplodingModel())
        ctrl._on_table_selection(idx, None)

        ctx_svc.update_selection.assert_not_called()

    def test_on_selection_none_track_does_not_update(self):
        """get_trackref that returns None should not update context."""
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = DummyNoneModel()

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        idx = DummyIndex(model=DummyNoneModel())
        ctrl._on_table_selection(idx, None)

        ctx_svc.update_selection.assert_not_called()

    def test_on_selection_invalid_proxy_no_fallback_no_update(self):
        """Invalid proxy + no registry + no global model = no context update."""
        ctx_svc = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx_svc
        win._ctx.model = None

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)

        idx = DummyIndex(model=DummyInvalidProxyModel())
        ctrl._on_table_selection(idx, None)

        ctx_svc.update_selection.assert_not_called()
