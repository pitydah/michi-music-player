import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Menu {
    id: root

    property var bridge: null
    property var selectionController: null
    property var trackModel: null

    objectName: "library.trackContextMenu"
    Accessible.role: Accessible.PopupMenu
    Accessible.name: "Menú contextual"

    function _selectedIds() {
        return root.selectionController ? root.selectionController.selectedIds : []
    }

    function _findTrackData(trackId, roleKey) {
        if (!root.trackModel) return ""
        for (var i = 0; i < root.trackModel.count; i++) {
            var idx = root.trackModel.index(i, 0)
            var tid = root.trackModel.data(idx, 0x0101)
            if (tid === trackId) {
                var mapping = {
                    "albumKey": 0x0106, "artist": 0x0104
                }
                var role = mapping[roleKey]
                if (role) return root.trackModel.data(idx, role)
                break
            }
        }
        return ""
    }

    MenuItem {
        text: qsTr("Reproducir")
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.playTrackById)
                root.bridge.playTrackById(ids[0])
        }
    }

    MenuItem {
        text: qsTr("Reproducir siguiente")
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.playNextTrackById)
                root.bridge.playNextTrackById(ids[0])
        }
    }

    MenuItem {
        text: qsTr("Añadir a la cola")
        onTriggered: {
            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.enqueueTrackById)
                    root.bridge.enqueueTrackById(ids[i])
            }
        }
    }

    MenuItem {
        text: qsTr("Reemplazar cola")
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
        text: qsTr("Favorito")
        onTriggered: {

            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.toggleFavoriteById)
                    root.bridge.toggleFavoriteById(ids[i])
            }
        }
    }

    MenuItem {

        text: qsTr("Añadir a playlist...")
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("playlists")
        }
    }

    MenuSeparator {}

    MenuItem {
        text: qsTr("Ir al álbum")
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0) {
                var ak = root._findTrackData(ids[0], "albumKey")
                if (ak && typeof navigationBridge !== "undefined")
                    navigationBridge.navigateWithParams("library.album_detail", {album_key: ak})

            }
        }
    }

    MenuItem {
        text: qsTr("Ir al artista")
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0) {

                var artist = root._findTrackData(ids[0], "artist")
                if (artist && typeof navigationBridge !== "undefined")
                    navigationBridge.navigateWithParams("library.artist_detail", {artist: artist})
            }
        }

    }

    MenuSeparator {}

    MenuItem {

        text: qsTr("Mostrar en carpeta")
        onTriggered: {
            var ids = root._selectedIds()
            if (ids.length > 0 && root.bridge && root.bridge.revealTrackById)
                root.bridge.revealTrackById(ids[0])
        }
    }


    MenuItem {
        text: qsTr("Editar metadatos")
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
        text: qsTr("Audio Lab")
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("audio_lab")
        }
    }

    MenuItem {
        text: qsTr("Verificar integridad")
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("library_doctor")
        }
    }

    MenuItem {
        text: qsTr("Enviar a dispositivo")
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("devices")
        }
    }

    MenuSeparator {}

    MenuItem {
        text: qsTr("Propiedades")
        onTriggered: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("metadata_inspector")
        }
    }

    MenuItem {
        text: qsTr("Eliminar de biblioteca")
        onTriggered: {
            var ids = root._selectedIds()
            for (var i = 0; i < ids.length; i++) {
                if (root.bridge && root.bridge.toggleFavoriteById)
                    root.bridge.toggleFavoriteById(ids[i])
            }
        }
        Accessible.description: "Elimina las canciones seleccionadas de la biblioteca"
    }
}
