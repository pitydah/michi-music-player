import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property alias text: field.text
    property alias placeholderText: field.placeholderText
    signal edited(string text)
    signal clearRequested()
    signal nextResultRequested()
    signal previousResultRequested()
    signal activateResultRequested()
    signal escapeRequested()
    implicitHeight: MichiMetrics.controlMedium
    implicitWidth: 260

    RowLayout {
        anchors.fill: parent
        spacing: 0
        MichiTextField {
            id: field
            Layout.fillWidth: true
            leftPadding: MichiSpacing.xl + MichiSpacing.sm
            rightPadding: root.text.length > 0 ? MichiSpacing.xl + MichiSpacing.sm : MichiSpacing.md
            onTextEdited: root.edited(text)
            Keys.onDownPressed: event => {
                root.nextResultRequested()
                event.accepted = true
            }
            Keys.onUpPressed: event => {
                root.previousResultRequested()
                event.accepted = true
            }
            Keys.onReturnPressed: event => {
                root.activateResultRequested()
                event.accepted = true
            }
            Keys.onEnterPressed: event => {
                root.activateResultRequested()
                event.accepted = true
            }
            Keys.onEscapePressed: event => {
                root.escapeRequested()
                event.accepted = true
            }
        }
    }
    MichiIcon {
        name: "search"
        width: MichiMetrics.iconSmall
        height: width
        anchors.left: parent.left
        anchors.leftMargin: MichiSpacing.md
        anchors.verticalCenter: parent.verticalCenter
        iconColor: field.activeFocus ? MichiPalette.auroraBlue : MichiPalette.textMuted
    }
    MichiIconButton {
        visible: root.text.length > 0
        iconName: "close"
        accessibleName: "Clear search"
        width: MichiMetrics.controlSmall
        height: width
        anchors.right: parent.right
        anchors.rightMargin: MichiSpacing.xs
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.clearRequested()
    }

    function forceInputFocus() { field.forceActiveFocus() }
}
