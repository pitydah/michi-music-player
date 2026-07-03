import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var playbackBridge: typeof playbackBridge !== "undefined" ? playbackBridge : null

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        contentHeight: column.height + MichiSpacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiSpacing.lg

            Text {
                text: "Reproducción"
                color: MichiColors.textPrimary
                font.pixelSize: MichiTypography.pageTitleSize
                font.weight: MichiTypography.weightSemiBold
            }

            GlassMaterial {
                width: parent.width
                height: 200
                radius: 16
                variant: "hero"

                Column {
                    anchors.centerIn: parent
                    spacing: MichiSpacing.md
                    width: parent.width * 0.80

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.playbackBridge ? root.playbackBridge.trackTitle : "Sin reproducción"
                        color: MichiColors.textPrimary
                        font.pixelSize: MichiTypography.sectionTitleSize
                        font.weight: MichiTypography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.playbackBridge ? root.playbackBridge.trackArtist : ""
                        color: MichiColors.textSecondary
                        font.pixelSize: MichiTypography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.playbackBridge ? root.playbackBridge.trackAlbum : ""
                        color: MichiColors.textMuted
                        font.pixelSize: MichiTypography.metaSize
                        visible: text !== ""
                    }

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiSpacing.md

                        ActionButton {
                            text: "<<"
                            variant: "ghost"
                            width: 40; height: 40
                            onClicked: { if (root.playbackBridge) root.playbackBridge.previous() }
                        }

                        ActionButton {
                            text: root.playbackBridge && root.playbackBridge.isPlaying ? "||" : ">"
                            variant: "primary"
                            width: 52; height: 52; radius: 26
                            onClicked: { if (root.playbackBridge) root.playbackBridge.togglePlay() }
                        }

                        ActionButton {
                            text: ">>"
                            variant: "ghost"
                            width: 40; height: 40
                            onClicked: { if (root.playbackBridge) root.playbackBridge.next() }
                        }
                    }
                }
            }

            SectionHeader { text: "Cola"; width: parent.width }

            GlassMaterial {
                width: parent.width
                radius: 12
                variant: "base"
                height: 120

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.lg
                    spacing: MichiSpacing.sm

                    Repeater {
                        model: root.playbackBridge ? root.playbackBridge.queue.slice(0, 5) : []

                        Row {
                            width: parent.width; height: 24; spacing: MichiSpacing.sm
                            Text {
                                text: modelData.title || "—"
                                color: MichiColors.textPrimary; font.pixelSize: MichiTypography.metaSize
                                elide: Text.ElideRight; width: parent.width * 0.5
                            }
                            Text {
                                text: modelData.artist || ""
                                color: MichiColors.textSecondary; font.pixelSize: MichiTypography.metaSize
                                elide: Text.ElideRight; width: parent.width * 0.4
                            }
                        }
                    }

                    Text {
                        text: root.playbackBridge && root.playbackBridge.queue.length === 0 ? "Cola vacía" : ""
                        color: MichiColors.textMuted; font.pixelSize: MichiTypography.metaSize
                        visible: text !== ""
                    }
                }
            }

            SectionHeader { text: "Historial"; width: parent.width }

            Text {
                text: root.playbackBridge && root.playbackBridge.history.length > 0 ? root.playbackBridge.history.length + " canciones" : "Sin historial"
                color: MichiColors.textMuted; font.pixelSize: MichiTypography.bodySize
            }
        }
    }
}
