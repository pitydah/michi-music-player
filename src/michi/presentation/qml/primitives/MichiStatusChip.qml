import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property string text: ""
    property string tone: "neutral"
    property bool dotVisible: true
    readonly property color toneColor: tone === "active" ? MichiPalette.auroraCyan
        : tone === "success" ? MichiPalette.success
        : tone === "warning" ? MichiPalette.warning
        : tone === "error" ? MichiPalette.error
        : MichiPalette.textSecondary

    implicitWidth: content.implicitWidth + MichiSpacing.md * 2
    implicitHeight: 24
    radius: MichiRadius.pill
    color: MichiSemanticColors.statusSurface(root.toneColor)
    border.width: 1
    border.color: MichiSemanticColors.statusBorder(root.toneColor)
    Accessible.role: Accessible.StaticText
    Accessible.name: root.text

    RowLayout {
        id: content
        anchors.centerIn: parent
        spacing: MichiSpacing.xs

        Rectangle {
            visible: root.dotVisible
            Layout.preferredWidth: 6
            Layout.preferredHeight: 6
            radius: 3
            color: root.toneColor
        }
        MichiText {
            text: root.text
            role: "technical"
            technical: true
            color: root.toneColor
            font.weight: Font.DemiBold
        }
    }
}
