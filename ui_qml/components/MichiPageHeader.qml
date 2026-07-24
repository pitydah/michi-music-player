import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property var actions: []
    property bool showBackButton: false

    signal backClicked()
    signal actionClicked(int index)

    implicitHeight: column.implicitHeight
    implicitWidth: parent ? parent.width : 400

    ColumnLayout {
        id: column
        width: parent.width
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: qsTr("< Volver")
                variant: "ghost"
                visible: root.showBackButton
                onClicked: root.backClicked()
                Accessible.name: qsTr("Volver a la página anterior")
            }

            Label {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Layout.fillWidth: true
                elide: Text.ElideRight
                accessibleRole: Accessible.Heading
            }

            Repeater {
                model: root.actions
                MichiButton {
                    text: modelData.text || ""
                    variant: modelData.variant || "ghost"
                    enabled: modelData.enabled !== false
                    onClicked: root.actionClicked(index)
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.subtitle !== ""
            text: root.subtitle
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
        }
    }
}
