import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Popup {
    id: root
    objectName: "LibraryContextMenu"

    property var bridge: null
    property var actionRegistry: null
    property int trackId: 0
    property string trackTitle: ""
    property string trackArtist: ""
    property string trackAlbum: ""
    property string albumKey: ""

    width: 260
    implicitHeight: menuColumn.implicitHeight + padding * 2
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: MichiTheme.spacing.xs

    function execute(actionId) {
        var result = null
        if (!root.bridge && actionId !== "track_open_album" && actionId !== "track_open_artist")
            return
        switch (actionId) {
        case "track_play_now":
            result = root.bridge.playTrackById(root.trackId)
            break
        case "track_add_to_queue":
            result = root.bridge.enqueueTrackById(root.trackId)
            break
        case "track_favorite":
            result = root.bridge.toggleFavoriteById(root.trackId)
            break
        case "track_open_album":
            if (root.albumKey && typeof navigationBridge !== "undefined")
                navigationBridge.navigateWithParams("library.album_detail", {album_key: root.albumKey})
            break
        case "track_open_artist":
            if (root.trackArtist && typeof navigationBridge !== "undefined")
                navigationBridge.navigateWithParams("library.artist_detail", {artist: root.trackArtist})
            break
        case "track_open_folder":
            result = root.bridge.revealTrackById(root.trackId)
            break
        }
        root.close()
    }

    background: Rectangle {
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        Accessible.role: Accessible.Menu
        Accessible.name: qsTr("Acciones de canción")
    }

    contentItem: ColumnLayout {
        id: menuColumn
        spacing: 2

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceSubtle

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                anchors.topMargin: MichiTheme.spacing.sm
                anchors.bottomMargin: MichiTheme.spacing.sm
                spacing: 1

                Text {
                    Layout.fillWidth: true
                    text: root.trackTitle || qsTr("Canción")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: root.trackArtist || root.trackAlbum
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    elide: Text.ElideRight
                }
            }
        }

        Repeater {
            model: [
                { label: qsTr("Reproducir ahora"), actionId: "track_play_now", glyph: "▶", enabled: true },
                { label: qsTr("Añadir a la cola"), actionId: "track_add_to_queue", glyph: "+", enabled: true },
                { label: qsTr("Marcar o quitar favorito"), actionId: "track_favorite", glyph: "♡", enabled: true },
                { label: qsTr("Abrir álbum"), actionId: "track_open_album", glyph: "▣", enabled: root.albumKey !== "" },
                { label: qsTr("Abrir artista"), actionId: "track_open_artist", glyph: "◎", enabled: root.trackArtist !== "" },
                { label: qsTr("Mostrar en carpeta"), actionId: "track_open_folder", glyph: "↗", enabled: true }
            ]

            Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                radius: MichiTheme.radius.sm
                color: actionMouse.containsMouse && modelData.enabled
                       ? MichiTheme.colors.surfaceHover
                       : "transparent"
                opacity: modelData.enabled ? 1.0 : MichiTheme.opacity.disabled

                Accessible.role: Accessible.MenuItem
                Accessible.name: modelData.label
                Accessible.onPressAction: {
                    if (modelData.enabled) root.execute(modelData.actionId)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.sm

                    Text {
                        Layout.preferredWidth: 22
                        text: modelData.glyph
                        color: actionMouse.containsMouse ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                    }
                    Text {
                        Layout.fillWidth: true
                        text: modelData.label
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: actionMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: modelData.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        if (modelData.enabled) root.execute(modelData.actionId)
                    }
                }
            }
        }
    }
}
