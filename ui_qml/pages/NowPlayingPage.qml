import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property string trackTitle: ""
    property string trackArtist: ""
    property string trackAlbum: ""
    property bool isPlaying: false
    property int position: 0
    property int duration: 0

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.03, 0.05, 0.95)

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiSpacing.md
            spacing: MichiSpacing.lg

            Item {
                width: parent.width * 0.30
                height: parent.height

                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiSpacing.md

                    Rectangle {
                        width: 48
                        height: 48
                        radius: 6
                        color: Qt.rgba(1.0, 1.0, 1.0, 0.04)

                        Text {
                            anchors.centerIn: parent
                            text: root.trackTitle ? root.trackTitle.charAt(0).toUpperCase() : "M"
                            color: MichiColors.accentBlue
                            font.pixelSize: 20
                            font.weight: MichiTypography.weightBold
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: root.trackTitle || "Sin reproducción"
                            color: MichiColors.textPrimary
                            font.pixelSize: MichiTypography.bodySize
                            font.weight: MichiTypography.weightMedium
                            elide: Text.ElideRight
                            width: 200
                        }

                        Text {
                            text: root.trackArtist ? root.trackArtist + (root.trackAlbum ? " · " + root.trackAlbum : "") : ""
                            color: MichiColors.textSecondary
                            font.pixelSize: MichiTypography.metaSize
                            elide: Text.ElideRight
                            width: 200
                            visible: text !== ""
                        }
                    }
                }
            }

            Item {
                width: parent.width * 0.40
                height: parent.height

                Column {
                    anchors.centerIn: parent
                    spacing: MichiSpacing.sm

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiSpacing.md

                        ActionButton {
                            text: "⏮"
                            variant: "ghost"
                            width: 36; height: 36
                        }

                        ActionButton {
                            text: root.isPlaying ? "⏸" : "▶"
                            variant: "primary"
                            width: 44; height: 44
                            radius: 22
                        }

                        ActionButton {
                            text: "⏭"
                            variant: "ghost"
                            width: 36; height: 36
                        }
                    }

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiSpacing.sm

                        Text {
                            text: formatTime(root.position)
                            color: MichiColors.textMuted
                            font.pixelSize: MichiTypography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Rectangle {
                            width: 200
                            height: 4
                            radius: 2
                            color: Qt.rgba(1.0, 1.0, 1.0, 0.08)
                            anchors.verticalCenter: parent.verticalCenter

                            Rectangle {
                                width: root.duration > 0 ? parent.width * (root.position / root.duration) : 0
                                height: parent.height
                                radius: 2
                                color: MichiColors.accentBlue
                            }
                        }

                        Text {
                            text: formatTime(root.duration)
                            color: MichiColors.textMuted
                            font.pixelSize: MichiTypography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Item {
                width: parent.width * 0.20
                height: parent.height

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiSpacing.sm

                    StatusBadge {
                        text: root.isPlaying ? "Reproduciendo" : "En pausa"
                        kind: root.isPlaying ? "active" : "disconnected"
                    }
                }
            }
        }
    }

    function formatTime(secs) {
        if (secs <= 0) return "0:00"
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
