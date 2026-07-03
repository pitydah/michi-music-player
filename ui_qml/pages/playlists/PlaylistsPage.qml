import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var playlistsBridge: typeof playlistsBridge !== "undefined" ? playlistsBridge : null

    Component.onCompleted: {
        if (root.playlistsBridge && typeof root.playlistsBridge.refresh !== "undefined")
            root.playlistsBridge.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Playlists"; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Gestiona tus listas de reproducción."; color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "+ Nueva playlist"; variant: "primary" }
                MichiButton { text: "Importar M3U"; variant: "secondary" }
            }

            SectionHeader { text: "Tus playlists"; width: parent.width }

            Flow {
                width: parent.width; spacing: MichiTheme.spacing.md

                Repeater {
                    model: root.playlistsBridge ? root.playlistsBridge.playlists : []

                    PlaylistCard {
                        playlistTitle: modelData.title || ""
                        trackCount: modelData.track_count || 0
                        duration: modelData.duration || ""
                        coverKey: modelData.cover_key || ""
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("playlist_detail")
                        }
                    }
                }
            }

            StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
        }
    }
}
