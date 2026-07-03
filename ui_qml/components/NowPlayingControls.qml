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
            iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
            iconText: "S"
            tooltipText: "Aleatorio"
            selected: root.shuffleEnabled
            btnSize: 34
            onClicked: root.shuffleClicked()
        }

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
            iconText: "<<"
            tooltipText: "Anterior"
            btnSize: 34
            onClicked: root.prevClicked()
        }

        Item {
            width: 44
            height: 44

            Rectangle {
                anchors.fill: parent
                radius: MichiTheme.radiusPill
                color: maPlay.containsMouse ? Qt.rgba(1,1,1,0.12) : MichiTheme.colors.accentBlue
                Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }

                Image {
                    anchors.centerIn: parent
                    width: 20
                    height: 20
                    source: root.isPlaying ? "../../icons/nowplaying_clean/warm_pause_32.png" : "../../icons/nowplaying_clean/warm_play_32.png"
                    sourceSize.width: 32
                    sourceSize.height: 32
                    fillMode: Image.PreserveAspectFit
                }
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
            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
            iconText: ">>"
            tooltipText: "Siguiente"
            btnSize: 34
            onClicked: root.nextClicked()
        }

        MichiIconButton {
            iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
            iconText: root.repeatMode === "one" ? "1" : "R"
            tooltipText: "Repetir"
            selected: root.repeatMode !== "none"
            btnSize: 34
            onClicked: root.repeatClicked()
        }
    }
}
