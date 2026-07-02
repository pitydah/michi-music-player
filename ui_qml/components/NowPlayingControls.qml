import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property bool isPlaying: false
    property bool shuffleEnabled: false
    property string repeatMode: "none"

    signal playClicked()
    signal prevClicked()
    signal nextClicked()
    signal shuffleClicked()
    signal repeatClicked()

    implicitHeight: 36

    Row {
        anchors.centerIn: parent
        spacing: MichiSpacing.sm

        Item {
            width: 34; height: 34
            GlassMaterial {
                anchors.fill: parent; radius: 17
                variant: root.shuffleEnabled ? "accent" : "status"
                hovered: shuffleMouse.containsMouse
                interactive: true
                MouseArea {
                    id: shuffleMouse; anchors.fill: parent
                    hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.shuffleClicked()
                }
                Text {
                    anchors.centerIn: parent
                    text: "S"
                    color: root.shuffleEnabled ? MichiColors.accentBlue : MichiColors.textMuted
                    font.pixelSize: 12; font.weight: MichiTypography.weightBold
                }
            }
        }

        ActionButton {
            text: "<<"
            variant: "ghost"; width: 34; height: 34
            onClicked: root.prevClicked()
        }

        ActionButton {
            text: root.isPlaying ? "||" : ">"
            variant: "primary"; width: 44; height: 44; radius: 22
            onClicked: root.playClicked()
        }

        ActionButton {
            text: ">>"
            variant: "ghost"; width: 34; height: 34
            onClicked: root.nextClicked()
        }

        Item {
            width: 34; height: 34
            GlassMaterial {
                anchors.fill: parent; radius: 17
                variant: root.repeatMode !== "none" ? "accent" : "status"
                hovered: repeatMouse.containsMouse
                interactive: true
                MouseArea {
                    id: repeatMouse; anchors.fill: parent
                    hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.repeatClicked()
                }
                Text {
                    anchors.centerIn: parent
                    text: root.repeatMode === "one" ? "1" : "R"
                    color: root.repeatMode !== "none" ? MichiColors.accentBlue : MichiColors.textMuted
                    font.pixelSize: 12; font.weight: MichiTypography.weightBold
                }
            }
        }
    }
}
