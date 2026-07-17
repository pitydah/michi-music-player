import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root
    objectName: "nowPlayingUtilityControls"

    property bool eqSupported: true
    property bool transmitActive: false
    property string transmitDeviceName: ""
    property bool transmitSupported: true

    signal eqClicked()
    signal transmitClicked()
    signal outputClicked()
    signal miniPlayerClicked()

    implicitHeight: 44
    implicitWidth: childrenRect.width

    Row {
        anchors.verticalCenter: parent.verticalCenter
        spacing: MichiTheme.spacing.xs

        UtilityButton {
            iconSource: "../../icons/nowplaying_clean/warm_eq_32.png"
            iconVisualSize: 24
            btnSize: 40
            tooltipText: "Ecualizador"
            enabled: root.eqSupported
            onClicked: root.eqClicked()
        }

        UtilityButton {
            iconSource: "../../icons/nowplaying_clean/warm_transmit_32.png"
            iconVisualSize: 24
            btnSize: 40
            tooltipText: root.transmitActive && root.transmitDeviceName ? root.transmitDeviceName : "Transmitir a dispositivo"
            enabled: root.transmitSupported
            active: root.transmitActive
            activeColor: MichiTheme.colors.nowPlayingTransmitActive
            activeBorderColor: MichiTheme.colors.nowPlayingTransmitActiveBorder
            onClicked: root.transmitClicked()
        }

        UtilityButton {
            iconSource: "../../icons/nowplaying_clean/warm_audio_source_32.png"
            iconVisualSize: 22
            btnSize: 44
            tooltipText: "Seleccionar salida de audio"
            onClicked: root.outputClicked()
        }

        UtilityButton {
            iconSource: "../../icons/nowplaying_clean/warm_mini_player_32.png"
            iconVisualSize: 22
            btnSize: 44
            tooltipText: "Abrir mini reproductor"
            onClicked: root.miniPlayerClicked()
        }
    }

    component UtilityButton: Item {
        id: btn
        property int btnSize: 40
        property int iconVisualSize: 22
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
                if (btn.active && btnMa.containsMouse) return Qt.rgba(52/255, 199/255, 89/255, 0.18)
                if (btn.active) return btn.activeColor
                if (btnMa.containsMouse) return Qt.rgba(1, 1, 1, 0.06)
                return "transparent"
            }
            border.width: 1
            border.color: {
                if (!enabled) return "transparent"
                if (btn.active && btnMa.containsMouse) return Qt.rgba(52/255, 199/255, 89/255, 0.34)
                if (btn.active) return btn.activeBorderColor
                if (btnMa.containsMouse) return Qt.rgba(1, 1, 1, 0.10)
                return "transparent"
            }
            opacity: enabled ? 1.0 : 0.35

            Image {
                anchors.centerIn: parent
                source: btn.iconSource
                sourceSize.width: btn.iconVisualSize
                sourceSize.height: btn.iconVisualSize
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
            Accessible.name: tooltipText
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
