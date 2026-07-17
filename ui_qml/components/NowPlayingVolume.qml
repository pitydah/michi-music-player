import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    objectName: "nowPlayingVolume"
    focus: true
    id: root

    property int volume: 80
    property bool muted: false
    property bool volumeSupported: true
    property bool muteSupported: true

    signal volumeAdjusted(int vol)
    signal muteClicked()

    implicitHeight: 24
    implicitWidth: 100

    Accessible.name: "Volumen"
    Accessible.description: "Control de volumen de reproducción"

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        Item {
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            Accessible.description: "Activar o desactivar el silencio"
            GlassMaterial {
                anchors.fill: parent; radius: MichiTheme.radius.lg
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
                    width: 13; height: 13
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
            Layout.fillWidth: true
            height: 5

            Rectangle {
                anchors.fill: parent
                radius: MichiTheme.radius.xs
                color: MichiTheme.colors.controlTrack
                clip: true

                Rectangle {
                    height: parent.height
                    width: parent.width * Math.min(1.0, root.volume / 100.0)
                    radius: MichiTheme.radius.xs
                    color: root.muted ? MichiTheme.colors.textMuted : MichiTheme.colors.accentBlue
                }
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
