import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var albums: []
    property var bridge: null

    signal albumClicked(string key, string title, string artist, int year)

    GridView {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albums
        cellWidth: 200; cellHeight: 260
        clip: true; boundsBehavior: Flickable.StopAtBounds

        delegate: AlbumCard {
            width: 180; height: 240
            albumTitle: modelData.title || modelData.album_key || ""
            albumArtist: modelData.artist || ""
            trackCount: modelData.track_count || 0
            onClicked: root.albumClicked(modelData.album_key || "", modelData.title || modelData.album_key || "", modelData.artist || "", modelData.year || 0)
        }

        Item { anchors.centerIn: parent; width: 300; height: 180; visible: root.albums.length === 0
            Column { anchors.centerIn: parent; spacing: MichiTheme.spacing.lg
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 48; height: 48; radius: 12; color: MichiTheme.colors.accentSurface
                    Text { anchors.centerIn: parent; text: "AL"; color: MichiTheme.colors.accentBlue; font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold; opacity: 0.7 } }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No hay álbumes"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "La biblioteca no tiene álbumes detectados."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm
                    MichiButton { text: "Refrescar"; variant: "primary"; onClicked: { if (root.bridge && typeof root.bridge.refresh !== "undefined") root.bridge.refresh() } }
                    MichiButton { text: "Ajustes"; variant: "ghost"; onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("settings") } }
                }
            }
        }
    }
}
