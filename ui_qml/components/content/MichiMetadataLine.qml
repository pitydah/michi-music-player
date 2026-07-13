import QtQuick
import QtQuick.Controls
import "../../theme"

Item {
    id: root

    property string label: ""
    property string value: ""
    property string details: ""

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitHeight: MichiTheme.rowHeightCompact
    Accessible.role: Accessible.StaticText
    Accessible.name: label
    Accessible.description: value + (details !== "" ? ". " + details : "")

    Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; width: parent.width * 0.34; text: root.label; color: MichiTheme.colors.textSecondary; elide: Text.ElideRight }
    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: parent.width * 0.62; text: root.value; color: MichiTheme.colors.textPrimary; horizontalAlignment: Text.AlignRight; elide: Text.ElideMiddle }
}
