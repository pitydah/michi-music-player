import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

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

    implicitHeight: 40

    Row {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        MichiIconButton {
            iconText: "S"
            tooltipText: "Aleatorio"
            selected: root.shuffleEnabled
            btnSize: 34
            onClicked: root.shuffleClicked()
        }

        MichiIconButton {
            iconText: "<<"
            tooltipText: "Anterior"
            btnSize: 34
            onClicked: root.prevClicked()
        }

        Rectangle {
            width: 44
            height: 44
            radius: MichiTheme.radiusPill
            color: maPlay.containsMouse ? Qt.rgba(1,1,1,0.12) : MichiTheme.colors.accentBlue
            Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

            Text {
                anchors.centerIn: parent
                text: root.isPlaying ? "||" : ">"
                font.pixelSize: 18
                font.weight: MichiTheme.typography.weightBold
                color: MichiTheme.colors.textOnAccent
            }
            MouseArea {
                id: maPlay
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.playClicked()
            }
        }

        MichiIconButton {
            iconText: ">>"
            tooltipText: "Siguiente"
            btnSize: 34
            onClicked: root.nextClicked()
        }

        MichiIconButton {
            iconText: root.repeatMode === "one" ? "1" : "R"
            tooltipText: "Repetir"
            selected: root.repeatMode !== "none"
            btnSize: 34
            onClicked: root.repeatClicked()
        }
    }
}
