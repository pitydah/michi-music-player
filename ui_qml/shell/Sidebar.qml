import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"
import "../components"

Item {
    id: root

    property string currentRoute: "home"
    signal routeRequested(string route)

    width: MichiTheme.sidebarWidth

    SidebarMaterial {
        anchors.fill: parent

        Column {
            anchors.fill: parent
            spacing: 0

            Column {
                width: parent.width
                anchors.topMargin: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.xs
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.sm

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.spacing.lg
                    text: "Michi"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    height: 36
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.spacing.lg
                    text: "Music Player"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    height: 18
                }
            }

            Rectangle {
                width: parent.width - MichiTheme.spacing.xl * 2
                height: 1
                color: MichiTheme.colors.borderSubtle
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Flickable {
                width: parent.width
                height: Math.min(contentHeight, parent.height - 180)
                contentHeight: navColumn.height + MichiTheme.spacing.lg
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height

                Column {
                    id: navColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    topPadding: MichiTheme.spacing.sm
                    spacing: 2

                    Repeater {
                        model: ListModel {
                            ListElement { route: "home"; glyph: "IN"; label: "Inicio" }
                            ListElement { route: "library"; glyph: "BL"; label: "Biblioteca" }
                            ListElement { route: "mix"; glyph: "MX"; label: "Mix" }
                            ListElement { route: "playback"; glyph: "RP"; label: "Reproducción" }
                            ListElement { route: "connections"; glyph: "SV"; label: "Conexiones" }
                            ListElement { route: "radio"; glyph: "RD"; label: "Radio" }
                            ListElement { route: "playlists"; glyph: "PL"; label: "Playlists" }
                            ListElement { route: "home_audio"; glyph: "HA"; label: "Home Audio" }
                            ListElement { route: "assistant"; glyph: "AI"; label: "Michi AI" }
                            ListElement { route: "audio_lab"; glyph: "AL"; label: "Audio Lab" }
                        }

                        SidebarItem {
                            property string glyphText: model.glyph
                            iconText: model.glyph
                            label: model.label
                            active: root.currentRoute === model.route
                            onClicked: root.routeRequested(model.route)
                        }
                    }
                }
            }

            Item { height: MichiTheme.spacing.xl; width: 1 }

            StatusBadge {
                anchors.left: parent.left
                anchors.leftMargin: MichiTheme.spacing.lg
                text: "Experimental"
                kind: "experimental"
            }
        }
    }
}
