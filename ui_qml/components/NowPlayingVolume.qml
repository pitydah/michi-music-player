import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property int volume: 80
    property bool muted: false

    signal volumeAdjusted(int vol)
    signal muteClicked()

    implicitHeight: 24

    Row {
        anchors.centerIn: parent
        spacing: MichiSpacing.sm

        Item {
            width: 28; height: 28
            GlassMaterial {
                anchors.fill: parent; radius: 14
                variant: root.muted ? "status" : "status"
                hovered: muteMouse.containsMouse
                interactive: true
                MouseArea {
                    id: muteMouse; anchors.fill: parent
                    hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.muteClicked()
                }
                Text {
                    anchors.centerIn: parent
                    text: root.muted || root.volume === 0 ? "X" : root.volume < 40 ? "V" : "V"
                    color: root.muted ? MichiColors.textMuted : MichiColors.textPrimary
                    font.pixelSize: 12; font.weight: MichiTypography.weightBold
                }
            }
        }

        Rectangle {
            width: 64; height: 4; radius: 2
            color: Qt.rgba(1.0, 1.0, 1.0, 0.10)
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                width: parent.width * (root.volume / 100.0)
                height: parent.height; radius: 2
                color: root.muted ? MichiColors.textMuted : MichiColors.accentBlue
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
