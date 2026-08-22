import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    property string title: qsTr("Track information")
    property var rows: []
    signal closeRequested()
    elevation: "elevated"
    accented: true
    accentColor: MichiPalette.auroraCyan
    implicitWidth: 320
    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.md
        RowLayout {
            Layout.fillWidth: true
            MichiText { Layout.fillWidth: true; text: root.title; role: "section" }
            MichiIconButton { iconName: "close"; accessibleName: "Close inspector"; onClicked: root.closeRequested() }
        }
        Repeater {
            model: root.rows
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                MichiText { Layout.preferredWidth: 108; text: modelData.label; role: "secondary" }
                MichiText { Layout.fillWidth: true; text: modelData.value; role: "technical"; technical: true; elide: Text.ElideMiddle }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
