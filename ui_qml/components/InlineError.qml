import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string message: ""
    property bool dismissible: true
    property string objectName: "inlineError"

    signal dismissed()

    implicitHeight: visible ? Math.max(36, row.implicitHeight + MichiTheme.spacing.sm * 2) : 0
    visible: root.message !== ""

    Accessible.role: Accessible.Alert
    Accessible.name: root.message

    Keys.onEscapePressed: {
        if (root.dismissible) root.dismissed()
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: MichiTheme.colors.error
        clip: true

        Row {
            id: row
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Text {
                width: parent.width - (root.dismissible ? 36 : 0)
                text: root.message
                color: MichiTheme.colors.textOnError
                font.pixelSize: MichiTheme.typography.metaSize
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Cerrar"
                color: MichiTheme.colors.textOnError
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.dismissible
                anchors.verticalCenter: parent.verticalCenter

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.dismissed()
                }
            }
        }
    }
}
