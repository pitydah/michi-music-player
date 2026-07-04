import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property int volume: 80
    property bool muted: false
    property bool enabled: true

    signal volumeAdjusted(int vol)
    signal muteClicked()

    implicitHeight: 24
    opacity: root.enabled ? 1.0 : 0.35

    Row {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        Item {
            width: 28; height: 28
            GlassMaterial {
                anchors.fill: parent; radius: 14
                variant: "status"
                hovered: root.enabled && muteMouse.containsMouse
                interactive: root.enabled
                MouseArea {
                    id: muteMouse; anchors.fill: parent
                    hoverEnabled: root.enabled
                    cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: { if (root.enabled) root.muteClicked() }
                }
                Image {
                    anchors.centerIn: parent
                    width: 16
                    height: 16
                    source: root.muted || root.volume === 0
                        ? "../../icons/nowplaying_clean/warm_mute_32.png"
                        : root.volume < 40
                            ? "../../icons/nowplaying_clean/warm_vol_low_32.png"
                            : "../../icons/nowplaying_clean/warm_vol_high_32.png"
                    sourceSize.width: 32
                    sourceSize.height: 32
                    fillMode: Image.PreserveAspectFit
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
                color: root.muted ? MichiTheme.colors.textMuted : MichiTheme.colors.accentBlue
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (root.enabled) {
                        var pct = Math.round((mouse.x / width) * 100)
                        root.volumeAdjusted(Math.max(0, Math.min(100, pct)))
                    }
                }
            }
        }
    }
}
