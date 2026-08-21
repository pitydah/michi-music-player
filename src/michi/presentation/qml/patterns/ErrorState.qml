import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    property string title: "Something went wrong"
    property string message: ""
    property string actionText: "Try again"
    signal actionRequested()
    elevation: "elevated"
    accented: true
    accentColor: MichiPalette.error
    implicitHeight: contentColumn.implicitHeight + MichiSpacing.xl * 2

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: MichiSpacing.sm
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiIcon {
                name: "info"
                Layout.preferredWidth: MichiMetrics.iconMedium
                Layout.preferredHeight: MichiMetrics.iconMedium
                iconColor: MichiPalette.error
            }
            MichiText { Layout.fillWidth: true; text: root.title; role: "section"; color: MichiPalette.error }
        }
        MichiText { Layout.fillWidth: true; text: root.message; role: "secondary"; wrapMode: Text.WordWrap }
        MichiButton {
            visible: root.actionText.length > 0
            text: root.actionText
            variant: "secondary"
            onClicked: root.actionRequested()
        }
    }
}
