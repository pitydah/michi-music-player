import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Item {
    id: root
    property string title: "Nothing here yet"
    property string message: ""
    property string actionText: ""
    property string iconName: "library"
    signal actionRequested()

    implicitHeight: 220
    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(420, root.width - MichiSpacing.xl * 2)
        spacing: MichiSpacing.sm
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 48
            Layout.preferredHeight: 48
            Layout.bottomMargin: MichiSpacing.sm
            radius: MichiRadius.lg
            color: MichiSemanticColors.controlSurface
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
            MichiIcon {
                anchors.centerIn: parent
                width: 24
                height: 24
                strokeWidth: 1.5
                name: root.iconName
                iconColor: MichiPalette.auroraCyan
            }
        }
        MichiText {
            Layout.fillWidth: true
            text: root.title
            role: "section"
            horizontalAlignment: Text.AlignHCenter
        }
        MichiText {
            Layout.fillWidth: true
            text: root.message
            role: "secondary"
            visible: text.length > 0
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
        MichiButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: MichiSpacing.sm
            visible: root.actionText.length > 0
            text: root.actionText
            onClicked: root.actionRequested()
        }
    }
}
