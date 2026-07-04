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
    implicitWidth: 100

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

        Rectangle {
            height: 4; radius: 2
            color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 24 - MichiTheme.spacing.xs

            Rectangle {
                width: parent.width * Math.min(1.0, root.volume / 100.0)
                height: parent.height; radius: 2
                color: root.muted ? MichiTheme.colors.textMuted : MichiTheme.colors.accentBlue
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var pct = Math.round((mouse.x / width) * 100)
                    root.volumeAdjusted(Math.max(0, Math.min(100, pct)))
                }
            }
        }
    }
}
