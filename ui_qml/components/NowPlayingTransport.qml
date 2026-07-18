import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root
    objectName: "nowPlayingTransport"

    property bool isPlaying: false
    property bool shuffleEnabled: false
    property string repeatMode: "none"
    property bool previousSupported: true
    property bool nextSupported: true
    property bool playPauseSupported: true
    property bool shuffleSupported: true
    property bool repeatSupported: true

    signal playClicked()
    signal prevClicked()
    signal nextClicked()
    signal shuffleClicked()
    signal repeatClicked()

    implicitHeight: 54
    implicitWidth: 240

    Row {
        anchors.centerIn: parent
        spacing: 11

        TransportButton {
            id: shuffleBtn
            btnSize: 40
            iconSize: 20
            iconSource: "../../icons/nowplaying_clean/warm_shuffle_32.png"
            tooltipText: root.shuffleSupported ? "Aleatorio" : "No soportado"
            enabled: root.shuffleSupported
            active: root.shuffleEnabled
            activeColor: MichiTheme.colors.nowPlayingShuffleActive
            activeBorderColor: MichiTheme.colors.nowPlayingShuffleActiveBorder
            onClicked: root.shuffleClicked()
        }

        TransportButton {
            id: prevBtn
            btnSize: 44
            iconSize: 26
            iconSource: "../../icons/nowplaying_clean/warm_prev_32.png"
            tooltipText: root.previousSupported ? "Anterior" : "No soportado"
            enabled: root.previousSupported
            onClicked: root.prevClicked()
        }

        Item {
            width: 54
            height: 54

            Rectangle {
                anchors.fill: parent
                radius: MichiTheme.radius.xl + 2
                color: {
                    if (!root.playPauseSupported) return "transparent"
                    if (playMa.containsPress) return MichiTheme.colors.nowPlayingTransportPressed
                    if (playMa.containsMouse) return MichiTheme.colors.nowPlayingTransportHover
                    return MichiTheme.colors.nowPlayingTransportBg
                }
                border.width: 1
                border.color: {
                    if (!root.playPauseSupported) return "transparent"
                    if (playMa.containsPress) return MichiTheme.colors.nowPlayingTransportBorder
                    if (playMa.containsMouse) return MichiTheme.colors.nowPlayingTransportHoverBorder
                    return MichiTheme.colors.nowPlayingTransportBorder
                }
                opacity: root.playPauseSupported ? 1.0 : 0.35

                Image {
                    anchors.centerIn: parent
                    source: root.isPlaying ? "../../icons/nowplaying_clean/warm_pause_32.png" : "../../icons/nowplaying_clean/warm_play_32.png"
                    sourceSize.width: root.isPlaying ? 32 : 34
                    sourceSize.height: root.isPlaying ? 32 : 34
                    fillMode: Image.PreserveAspectFit
                }

                MouseArea {
                    id: playMa
                    anchors.fill: parent
                    hoverEnabled: root.playPauseSupported
                    cursorShape: root.playPauseSupported ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: { if (root.playPauseSupported) root.playClicked() }
                }

                Accessible.role: Accessible.Button
                Accessible.name: root.isPlaying ? "Pausa" : "Reproducir"
                Accessible.description: root.playPauseSupported ? "" : "No soportado por el backend actual"
                activeFocusOnTab: root.playPauseSupported
                Keys.onSpacePressed: root.playClicked()
                Keys.onReturnPressed: root.playClicked()
            }

            Rectangle {
                anchors.centerIn: parent
                width: parent.width + 4
                height: parent.height + 4
                radius: MichiTheme.radius.xl + 4
                color: "transparent"
                border.width: parent.activeFocus ? 2 : 0
                border.color: MichiTheme.colors.borderFocus
                visible: parent.activeFocus
            }
        }

        TransportButton {
            id: nextBtn
            btnSize: 44
            iconSize: 26
            iconSource: "../../icons/nowplaying_clean/warm_next_32.png"
            tooltipText: root.nextSupported ? "Siguiente" : "No soportado"
            enabled: root.nextSupported
            onClicked: root.nextClicked()
        }

        TransportButton {
            id: repeatBtn
            btnSize: 40
            iconSize: 20
            iconSource: "../../icons/nowplaying_clean/warm_repeat_32.png"
            tooltipText: root.repeatSupported ? (root.repeatMode === "one" ? "Repetir una" : "Repetir todo") : "No soportado"
            enabled: root.repeatSupported
            active: root.repeatMode !== "none"
            activeColor: MichiTheme.colors.nowPlayingShuffleActive
            activeBorderColor: MichiTheme.colors.nowPlayingShuffleActiveBorder
            onClicked: root.repeatClicked()

            Rectangle {
                anchors.centerIn: parent; y: -2
                width: MichiTheme.spacing.sm + MichiTheme.spacing.xxs; height: width; radius: width / 2
                color: MichiTheme.colors.nowPlayingThumb
                visible: root.repeatMode === "one" && root.repeatSupported

                Text {
                    anchors.centerIn: parent
                    text: "1"
                    color: MichiTheme.colors.textOnAccent
                    font.pixelSize: MichiTheme.typography.badgeSize
                    font.weight: MichiTheme.typography.weightBold
                }
            }
        }
    }

    component TransportButton: Item {
        id: btn
        property int btnSize: 40
        property int iconSize: 20
        property string iconSource: ""
        property string tooltipText: ""
        property bool active: false
        property color activeColor: "transparent"
        property color activeBorderColor: "transparent"

        signal clicked()

        width: btnSize
        height: btnSize

        Rectangle {
            anchors.fill: parent
            radius: parent.width / 2
            color: {
                if (!enabled) return "transparent"
                if (btn.active && btnMa.containsMouse) return Qt.rgba(249/255, 33/255, 65/255, 0.18)
                if (btn.active) return Qt.rgba(249/255, 33/255, 65/255, 0.135)
                if (btnMa.containsMouse) return Qt.rgba(1, 1, 1, 0.08)
                return "transparent"
            }
            border.width: 1
            border.color: {
                if (!enabled) return "transparent"
                if (btn.active && btnMa.containsMouse) return Qt.rgba(249/255, 33/255, 65/255, 0.32)
                if (btn.active) return Qt.rgba(249/255, 33/255, 65/255, 0.26)
                if (btnMa.containsMouse) return Qt.rgba(1, 1, 1, 0.12)
                return "transparent"
            }
            opacity: enabled ? 1.0 : 0.35

            Image {
                anchors.centerIn: parent
                source: btn.iconSource
                sourceSize.width: btn.iconSize
                sourceSize.height: btn.iconSize
                fillMode: Image.PreserveAspectFit
            }

            MouseArea {
                id: btnMa
                anchors.fill: parent
                hoverEnabled: enabled
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: { if (enabled) btn.clicked() }
            }

            Accessible.role: Accessible.Button
            Accessible.name: btn.tooltipText
            Accessible.description: enabled ? "" : "No soportado por el backend actual"
            activeFocusOnTab: enabled
            Keys.onSpacePressed: btn.clicked()
            Keys.onReturnPressed: btn.clicked()
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width + 4
            height: parent.height + 4
            radius: (parent.width + 4) / 2
            color: "transparent"
            border.width: parent.activeFocus ? 2 : 0
            border.color: MichiTheme.colors.borderFocus
            visible: parent.activeFocus
        }

        ToolTip {
            visible: btnMa.containsMouse && tooltipText !== ""
            text: tooltipText
            delay: 600
        }
    }
}
