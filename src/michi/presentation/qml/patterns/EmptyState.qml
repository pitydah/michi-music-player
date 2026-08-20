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
            Layout.preferredWidth: 52
            Layout.preferredHeight: 52
            Layout.bottomMargin: MichiSpacing.sm
            radius: MichiRadius.floating
            color: Qt.rgba(0.298, 0.651, 1, 0.08)
            border.width: 1
            border.color: Qt.rgba(0.298, 0.651, 1, 0.18)
            MichiIcon {
                anchors.centerIn: parent
                width: MichiMetrics.iconLarge
                height: width
                name: root.iconName
                iconColor: MichiPalette.auroraBlue
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
