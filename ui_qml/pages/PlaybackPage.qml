import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var pb: typeof playbackBridge !== "undefined" ? playbackBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property var ps: root.np || root.pb

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Reproducción"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            GlassPanel {
                width: parent.width
                height: 160

                Column {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    width: parent.width * 0.80

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.ps ? root.ps.trackTitle : "Sin reproducción"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.ps ? root.ps.trackArtist : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.ps ? root.ps.trackAlbum : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }

                    StatusBadge {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.ps && root.ps.isPlaying ? "Reproduciendo" : "Pausado"
                        kind: root.ps && root.ps.isPlaying ? "success" : "info"
                    }
                }
            }

            SectionHeader { text: "Cola"; width: parent.width }

            GlassPanel {
                width: parent.width
                height: Math.min(300, 24 * Math.max(1, (root.ps ? root.ps.queue.length : 0)) + 40)

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Repeater {
                        model: root.ps ? root.ps.queue.slice(0, 10) : []

                        Row {
                            width: parent.width; height: 24; spacing: MichiTheme.spacing.sm
                            Text {
                                text: modelData.title || "—"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; width: parent.width * 0.5
                            }
                            Text {
                                text: modelData.artist || ""
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; width: parent.width * 0.4
                            }
                        }
                    }

                    Text {
                        text: root.ps && root.ps.queue.length === 0 ? "Cola vacía" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                }
            }

            SectionHeader { text: "Historial"; width: parent.width }

            Text {
                text: root.ps && root.ps.history.length > 0
                      ? root.ps.history.length + " canciones"
                      : "Sin historial"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
