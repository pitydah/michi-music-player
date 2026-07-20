import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Inline Error"
    objectName: "inlineError"
    focus: true
    id: root

    property string message: ""
    property string actionText: ""
    property bool showDismiss: true
    property bool autoHide: false
    property int autoHideDuration: 5000

    signal dismissed()
    signal actionTriggered()


    Accessible.description: message

    implicitHeight: visible ? row.implicitHeight + MichiTheme.spacing.sm * 2 : 0
    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.badgeDangerBg
    border.color: MichiTheme.colors.error
    border.width: MichiTheme.borderWidth
    visible: message !== ""
    clip: true

    Behavior on implicitHeight {
        NumberAnimation {
            duration: MichiTheme.motion.durationFast
            easing.type: Easing.OutCubic
        }
    }

    Timer {
        id: hideTimer
        interval: root.autoHideDuration
        running: root.autoHide && root.visible
        onTriggered: {
            root.message = ""
            root.dismissed()
        }
    }

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.sm

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: qsTr("\u26A0")
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.bodySize
            Accessible.role: Accessible.Graphic
            Accessible.name: "Advertencia"
            Accessible.description: "Indicador de error"
        }

        Text {
            id: messageText
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(1, parent.width
                - (dismissBtn.implicitWidth + (actionBtn.visible ? actionBtn.implicitWidth : 0) + parent.spacing * 4))
            text: root.message
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            maximumLineCount: 2
        }

        QQC2.AbstractButton {
            id: actionBtn
            anchors.verticalCenter: parent.verticalCenter
            visible: root.actionText !== ""
            focusPolicy: Qt.StrongFocus


            contentItem: Text {
                text: root.actionText
                color: MichiTheme.colors.accentBlue
                font.pixelSize: MichiTheme.typography.captionSize
                font.weight: MichiTheme.typography.weightMedium
            }

            background: Item {}
            onClicked: root.actionTriggered()
        }

        MichiIconButton {
            id: dismissBtn
            anchors.verticalCenter: parent.verticalCenter
            visible: root.showDismiss
            iconSource: "../../icons/nav_back.svg"
            btnSize: 24
            tooltipText: "Cerrar"
            accessibleName: "Cerrar"
            accessibleDescription: "Descartar este mensaje de error"
            transform: Rotation { angle: 45 }
            onClicked: {
                root.message = ""
                root.dismissed()
            }
        }
    }
}
