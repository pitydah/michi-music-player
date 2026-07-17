import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Artist List"
    objectName: "artistList"
    focus: true
    id: root

    property var artists: []
    property var bridge: null

    signal artistSelected(string artistName)

    GridView {
        Accessible.role: Accessible.List

        Accessible.name: "Cuadrícula de artistas"

        activeFocusOnTab: true

        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.artists
        cellWidth: 190; cellHeight: 220
        clip: true; boundsBehavior: Flickable.StopAtBounds

        delegate: ArtistCard {
            width: 180; height: 200
            artistName: modelData.name || ""
            trackCount: modelData.track_count || 0
            albumCount: modelData.album_count || 0
            onClicked: root.artistSelected(modelData.name || "")
        }

        Item { anchors.centerIn: parent; width: 300; height: 180; visible: root.artists.length === 0
            Column { anchors.centerIn: parent; spacing: MichiTheme.spacing.lg
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 48; height: 48; radius: MichiTheme.radius.lg; color: MichiTheme.colors.accentSurface
                    Text { anchors.centerIn: parent; text: "AR"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightBold; opacity: MichiTheme.opacity.hover } }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No hay artistas"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Refresca la biblioteca o revisa los metadatos de artista."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm
                    MichiButton { text: "Refrescar"; variant: "primary"; onClicked: { if (root.bridge && typeof root.bridge.refresh !== "undefined") root.bridge.refresh() } }
                    MichiButton { text: "Ajustes"; variant: "ghost"; onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("settings") } }
                }
            }
        }
    }
}
