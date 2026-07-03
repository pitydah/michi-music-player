import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root

    property var pb: typeof playbackBridge !== "undefined" ? playbackBridge : null

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
                height: 200

                Column {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    width: parent.width * 0.80

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.pb ? root.pb.trackTitle : "Sin reproducción"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.pb ? root.pb.trackArtist : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.pb ? root.pb.trackAlbum : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiTheme.spacing.md

                        MichiIconButton {
                            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
                            iconText: "<<"
                            tooltipText: "Anterior"
                            btnSize: 40
                            onClicked: { if (root.pb) root.pb.previous() }
                        }

                        Rectangle {
                            width: 52; height: 52
                            radius: MichiTheme.radiusPill
                            color: maPlay.containsMouse ? Qt.rgba(1,1,1,0.12) : MichiTheme.colors.accentBlue
                            Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

                            Image {
                                anchors.centerIn: parent
                                width: 24
                                height: 24
                                source: root.pb && root.pb.isPlaying
                                    ? "../../icons/nowplaying_clean/warm_pause_32.png"
                                    : "../../icons/nowplaying_clean/warm_play_32.png"
                                sourceSize.width: 32
                                sourceSize.height: 32
                                fillMode: Image.PreserveAspectFit
                            }

                            MouseArea {
                                id: maPlay; anchors.fill: parent
                                hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { if (root.pb) root.pb.togglePlay() }
                            }
                        }

                        MichiIconButton {
                            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
                            iconText: ">>"
                            tooltipText: "Siguiente"
                            btnSize: 40
                            onClicked: { if (root.pb) root.pb.next() }
                        }
                    }
                }
            }

            SectionHeader { text: "Cola"; width: parent.width }

            GlassPanel {
                width: parent.width
                height: 120

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Repeater {
                        model: root.pb ? root.pb.queue.slice(0, 5) : []

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
                        text: root.pb && root.pb.queue.length === 0 ? "Cola vacía" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                }
            }

            SectionHeader { text: "Historial"; width: parent.width }

            Text {
                text: root.pb && root.pb.history.length > 0
                      ? root.pb.history.length + " canciones"
                      : "Sin historial"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
