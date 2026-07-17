import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Popup {
    id: root

    property var bridge: null
    property var actionRegistry: null
    property int trackId: 0
    property string trackTitle: ""
    property string trackArtist: ""
    property string trackAlbum: ""

    signal playClicked(int trackId)
    signal addToQueueClicked(int trackId)
    signal addToPlaylistClicked(int trackId)
    signal goToAlbumClicked(string album)
    signal goToArtistClicked(string artist)
    signal editMetadataClicked(int trackId)
    signal showInFolderClicked(int trackId)
    signal propertiesClicked(int trackId)

    width: 220
    height: Math.min(implicitHeight, 420)
    modal: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: MichiTheme.spacing.xs

    objectName: "LibraryContextMenu"

    background: Rectangle {
        Accessible.role: Accessible.PopupMenu
        Accessible.name: "Menú contextual"
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
    }

    Column {
        anchors.fill: parent
        spacing: 2

        Text {
            text: root.trackTitle
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightSemiBold
            bottomPadding: MichiTheme.spacing.xs
            elide: Text.ElideRight
            width: parent.width
            leftPadding: MichiTheme.spacing.sm
        }

        MenuSeparator { width: parent.width }

        Repeater {
            model: [
                {label: "Reproducir", action: "play"},
                {label: "Añadir a cola", action: "queue"},
                {label: "Añadir a playlist", action: "addPlaylist"},
                {label: "Ir al álbum", action: "goAlbum"},
                {label: "Ir al artista", action: "goArtist"},
                {label: "Editar metadatos", action: "editMeta"},
                {label: "Mostrar en carpeta", action: "showFolder"},
                {label: "Propiedades", action: "properties"},
            ]

            Item {
    focus: true
                width: parent.width
                height: 32

                Rectangle {
                    anchors.fill: parent
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm

                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: MichiTheme.spacing.sm
                        text: modelData.label
                        color: root.actionRegistry && root.actionRegistry.qmlGet("track_" + modelData.action)
                               ? (root.actionRegistry.qmlGet("track_" + modelData.action).destructive ? MichiTheme.colors.error : MichiTheme.colors.textPrimary)
                               : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    Accessible.onPressAction: {
                        if (root.actionRegistry)
                            root.actionRegistry.execute("track_" + modelData.action, [root.trackId])
                        root.close()
                    }

                    onClicked: {
                        if (root.actionRegistry)
                            root.actionRegistry.execute("track_" + modelData.action, [root.trackId])
                        root.close()
                    }
                }

                Keys.onReturnPressed: {
                    if (root.actionRegistry)
                        root.actionRegistry.execute("track_" + modelData.action, [root.trackId])
                    root.close()
                }
                Keys.onEnterPressed: {
                    if (root.actionRegistry)
                        root.actionRegistry.execute("track_" + modelData.action, [root.trackId])
                    root.close()
                }
            }
        }
    }
}
