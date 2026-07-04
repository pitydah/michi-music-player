import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property int volume: 80
    property bool muted: false
    property bool _enabled: root.enabled

    signal volumeAdjusted(int vol)
    signal muteClicked()

    implicitHeight: 24
    implicitWidth: 120

    Row {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Item {
            width: 24; height: 24
            anchors.verticalCenter: parent.verticalCenter
            GlassMaterial {
                anchors.fill: parent; radius: 12
                variant: "status"
                hovered: muteMouse.containsMouse
                MouseArea {
                    id: muteMouse; anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.muteClicked()
                }
                Image {
                    anchors.centerIn: parent
                    width: 14; height: 14
                    source: root.muted || root.volume === 0
                        ? "../../icons/nowplaying_clean/warm_mute_32.png"
                        : root.volume < 40
                            ? "../../icons/nowplaying_clean/warm_vol_low_32.png"
                            : "../../icons/nowplaying_clean/warm_vol_high_32.png"
                    sourceSize.width: 32; sourceSize.height: 32
                    fillMode: Image.PreserveAspectFit
                }
            }
        }

        Item {
            height: 4
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: muteIcon.right; anchors.leftMargin: MichiTheme.spacing.xs
            anchors.right: parent.right

            Rectangle {
                anchors.fill: parent
                radius: 2
                color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
                clip: true

                Rectangle {
                    width: parent.width * Math.min(1.0, root.volume / 100.0)
                    height: parent.height; radius: 2
                    color: root.muted ? MichiTheme.colors.textMuted : MichiTheme.colors.accentBlue
                }
            }

            MouseArea {
                id: volumeMouse
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var pct = Math.round((mouse.x / width) * 100)
                    root.volumeAdjusted(Math.max(0, Math.min(100, pct)))
                }
            }
        }
    }

    Item { id: muteIcon; width: 24; height: 24; visible: false }
}
