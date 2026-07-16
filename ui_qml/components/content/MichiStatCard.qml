import QtQuick
import QtQuick.Controls
import "../../theme"
import "../foundations"

FocusScope {
    id: root

    property string label: ""
    property string value: ""
    property string supportingText: ""
    property bool selected: false

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitWidth: 180
    implicitHeight: 104
    activeFocusOnTab: enabled
    Accessible.role: Accessible.Button
    Accessible.name: label
    Accessible.description: value + (supportingText !== "" ? ". " + supportingText : "")
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle { anchors.fill: parent; radius: MichiTheme.radiusMd; color: root.selected ? MichiTheme.colors.accentSelection : hover.hovered ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard; border.color: MichiTheme.colors.borderCard; border.width: MichiTheme.borderWidth }
    objectName: "michiStatCard"
    focus: true
    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xs
        Text { text: root.value; color: MichiTheme.colors.accent; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightBold }
        Text { width: parent.width; text: root.label; color: MichiTheme.colors.textPrimary; elide: Text.ElideRight }
        Text { width: parent.width; text: root.supportingText; color: MichiTheme.colors.textMuted; elide: Text.ElideRight; visible: text !== "" }
    }
    MichiFocusRing { control: root; controlRadius: MichiTheme.radiusMd }
    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked(); onDoubleTapped: root.doubleClicked() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: function(point) { root.contextRequested(point.position.x, point.position.y) } }
}
