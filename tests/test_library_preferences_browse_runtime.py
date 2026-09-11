"""POST-R4 P6 — Preferences deep-merge migration + AlbumBrowseState key.

- LibraryView.loadViewPreferences: un JSON persistido incompleto (V1)
  carga con deep-merge contra el schema actual: overrides preservados,
  secciones ausentes con defaults, sin warnings ni undefined;
- AlbumGridView productivo: la posición de browse se reconcilia por KEY
  cuando cambia el modelo (sort/filter/scan): si el álbum sigue
  existiendo, el índice se re-resuelve; si ya no existe, la selección se
  limpia (posición determinística) — nunca un salto a otro álbum.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QUrl  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from michi.application.settings_service import SettingsService  # noqa: E402
from michi.presentation.settings_bridge import SettingsBridge  # noqa: E402
from tests.conftest import FakeSettingsRepo  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


class _AlbumLibrary(QObject):
    albums = Property("QVariantList", lambda self: [])

    def select_album(self, key):  # pragma: no cover
        pass

    def play_album(self, key):  # pragma: no cover
        pass


def _album(key, title):
    return {
        "key": key,
        "title": title,
        "artist": "Artist",
        "artworkPath": "",
        "hasArtwork": False,
        "trackCount": 9,
        "durationMs": 1000,
        "year": 2000,
        "technicalSummary": "",
        "codecs": [],
    }


def _settings_bridge(library_views_json):
    settings = SettingsService(FakeSettingsRepo())
    bridge = SettingsBridge(settings)
    bridge.set_library_views(library_views_json)
    return bridge


class TestPreferencesMigration:
    def test_stale_v1_json_deep_merges_with_defaults(self, qapp):
        """JSON V1 con solo gallery + activeMode: las secciones ausentes
        (flow/vinyl/chronology/editorial/studioList) reciben defaults, el
        override gallery se preserva y trackTable sobrevive."""
        library = _AlbumLibrary()
        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        bridge = _settings_bridge(
            '{"activeMode": "grid", "sortMode": "year", "gallery": '
            '{"artworkSize": "large", "spacing": "airy"}}'
        )
        engine.rootContext().setContextProperty("library", library)
        engine.rootContext().setContextProperty("settingsBridge", bridge)
        component = QQmlComponent(engine, str(QML / "views" / "LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, errs
        obj = component.create()
        assert obj is not None
        QTest.qWait(80)
        prefs = obj.property("viewPreferences")
        import json as _json

        if hasattr(prefs, "toVariant"):
            prefs = prefs.toVariant()
        parsed = _json.loads(prefs) if isinstance(prefs, str) else prefs
        # override preservado
        assert parsed["gallery"]["artworkSize"] == "large"
        assert parsed["gallery"]["spacing"] == "airy"
        # secciones ausentes → defaults
        assert parsed["flow"]["coverSize"] == "standard"
        assert parsed["vinyl"]["sleeveSize"] == "standard"
        assert parsed["chronology"]["grouping"] == "decade"
        assert parsed["editorial"]["heroVisible"] is True
        assert parsed["studioList"]["artworkSize"] == "small"
        # sin metadataLevel huérfano en studioList (P5)
        assert "metadataLevel" not in parsed["studioList"]
        # root keys preservadas
        assert parsed["sortMode"] == "year"
        engine.deleteLater()


class TestAlbumBrowseReconcile:
    def _mount_grid(self, albums):
        library = _AlbumLibrary()
        view = QQuickView()
        view.engine().addImportPath(str(QML))
        view.rootContext().setContextProperty("library", library)
        view.setSource(QUrl.fromLocalFile(str(QML / "views" / "AlbumGridView.qml")))
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.setResizeMode(QQuickView.SizeRootObjectToView)
        view.resize(1000, 700)
        view.show()
        QTest.qWait(150)
        root = view.rootObject()
        root.setProperty("albumModel", albums)
        QTest.qWait(200)
        # browseState real (componente productivo) — creado con el engine
        # del view y retenido para que el GC no lo destruya.
        comp = QQmlComponent(view.engine(), str(QML / "views" / "AlbumBrowseState.qml"))
        state = comp.create()
        assert state is not None
        view._held = comp
        root.setProperty("browseState", state)
        QTest.qWait(120)
        return view, root, state

    def test_sort_reorder_keeps_browse_key(self, qapp):
        """Con el browse en el álbum 'a2' (índice 1), un reorder del
        modelo (a2 al frente) re-resuelve el índice por KEY — la posición
        sigue al álbum, no al número."""
        albums = [_album("a1", "Zulu"), _album("a2", "Alpha"), _album("a3", "Mike")]
        view, root, state = self._mount_grid(albums)
        try:
            state.setProperty("currentKey", "a2")
            root.setProperty("currentIndex", 1)
            QTest.qWait(120)
            assert root.property("currentIndex") == 1
            # sort: a2 pasa al frente
            root.setProperty("albumModel", [albums[1], albums[0], albums[2]])
            QTest.qWait(200)
            assert state.property("currentKey") == "a2"
            assert root.property("currentIndex") == 0, (
                "el índice se re-resuelve contra la key (nunca salta al "
                "álbum que ahora ocupa el índice viejo)"
            )
        finally:
            view.close()

    def test_removed_key_clears_to_deterministic_position(self, qapp):
        """El álbum del browse desaparece del modelo (filtro): la
        selección NUNCA se transfiere al álbum que ocupaba el índice
        viejo (a3) — la posición cae al índice determinístico 0 y la key
        del browse pasa a ser la del álbum en esa posición segura."""
        albums = [_album("a1", "Zulu"), _album("a2", "Alpha"), _album("a3", "Mike")]
        view, root, state = self._mount_grid(albums)
        try:
            state.setProperty("currentKey", "a2")
            root.setProperty("currentIndex", 1)
            QTest.qWait(120)
            # filtro: a2 fuera; el índice 1 lo ocupaba a3
            root.setProperty("albumModel", [albums[0], albums[2]])
            QTest.qWait(200)
            assert root.property("currentIndex") == 0, (
                "posición determinística segura (nunca el índice viejo 1)"
            )
            assert state.property("currentKey") != "a2", "la key muerta no persiste"
            assert state.property("currentKey") == "a1", (
                "la key del browse es la del álbum en la posición segura"
            )
        finally:
            view.close()
