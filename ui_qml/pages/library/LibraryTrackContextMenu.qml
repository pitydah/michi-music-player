import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Menu {
    id: root

    property var bridge: null
    property var selectionController: null
    property var trackModel: null
    property var actionRegistry: typeof actionRegistry !== "undefined" ? actionRegistry : null

    function _selectedIds() {
        return root.selectionController ? root.selectionController.selectedIds : []
    }

    MenuItem {
        text: "Reproducir"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.playTrackById)
                root.bridge.playTrackById(ids[0])
        }
    }

    MenuItem {
        text: "Reproducir siguiente"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.playNextTrackById)
                root.bridge.playNextTrackById(ids[0])
        }
    }

    MenuItem {
        text: "Añadir a la cola"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.enqueueTrackById)
                    root.bridge.enqueueTrackById(ids[i])
            }
        }
    }

    MenuItem {
        text: "Reemplazar cola"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.playTrackById)
                root.bridge.playTrackById(ids[0])
            for (var i = 1; i < ids.length; i++) {
                if (root.bridge && root.bridge.enqueueTrackById)
                    root.bridge.enqueueTrackById(ids[i])
            }
        }
    }

    MenuSeparator {}

    MenuItem {
        text: "Favorito"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.toggleFavoriteById)
                    root.bridge.toggleFavoriteById(ids[i])
            }
        }
    }

    MenuItem {
        text: "Añadir a playlist..."; icon.source: ""
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("playlists")
        }
    }

    MenuSeparator {}

    MenuItem {
        text: "Abrir álbum"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.trackModel) {
                var idx = root.trackModel.index(0, 0)
                for (var i = 0; i < root.trackModel.count; i++) {
                    var tid = root.trackModel.data(root.trackModel.index(i, 0), 0x0101)
                    if (tid === ids[0]) {
                        var ak = root.trackModel.data(root.trackModel.index(i, 0), 0x0106)
                        if (ak && typeof navigationBridge !== "undefined")
                            navigationBridge.navigateWithParams("library.album_detail", {album_key: ak})
                        break
                    }
                }
            }
        }
    }

    MenuItem {
        text: "Abrir artista"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.trackModel) {
                for (var i = 0; i < root.trackModel.count; i++) {
                    var tid = root.trackModel.data(root.trackModel.index(i, 0), 0x0101)
                    if (tid === ids[0]) {
                        var artist = root.trackModel.data(root.trackModel.index(i, 0), 0x0104)
                        if (artist && typeof navigationBridge !== "undefined")
                            navigationBridge.navigateWithParams("library.artist_detail", {artist: artist})
                        break
                    }
                }
            }
        }
    }

    MenuItem {
        text: "Abrir carpeta"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.revealTrackById)
                root.bridge.revealTrackById(ids[0])
        }
    }

    MenuSeparator {}

    MenuItem {
        text: "Editar metadatos"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && typeof navigationBridge !== "undefined") {
                if (typeof selectionContextBridge !== "undefined")
                    selectionContextBridge.setSelected({"id": ids[0]})
                navigationBridge.navigate("metadata_inspector")
            }
        }
    }

    MenuItem {
        text: "Audio Lab"; icon.source: ""
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("audio_lab")
        }
    }

    MenuItem {
        text: "Verificar integridad"; icon.source: ""
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("library_doctor")
        }
    }

    MenuItem {
        text: "Enviar a dispositivo"; icon.source: ""
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("devices")
        }
    }

    MenuSeparator {}

    MenuItem {
        text: "Propiedades"; icon.source: ""
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("metadata_inspector")
        }
    }

    MenuItem {
        text: "Eliminar de biblioteca"; icon.source: ""
        onTriggered: {
            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.toggleFavoriteById)
                    root.bridge.toggleFavoriteById(ids[i])
            }
        }
    }
}
