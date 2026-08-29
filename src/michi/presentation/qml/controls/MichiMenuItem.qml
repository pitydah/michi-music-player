import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

MenuItem {
    id: root

    implicitHeight: 36
    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.md

    contentItem: RowLayout {
        spacing: MichiSpacing.sm

        Item {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            MichiIcon {
                anchors.centerIn: parent
                width: 17
                height: 17
                visible: root.icon.name.length > 0
                name: root.icon.name
                iconColor: root.enabled
                    ? MichiPalette.textPrimary : MichiPalette.textDisabled
            }
            MichiText {
                anchors.centerIn: parent
                visible: root.checkable && root.icon.name.length === 0
                text: root.checked ? "✓" : ""
                role: "technical"
                technical: true
                color: MichiPalette.auroraCyan
            }
        }
        MichiText {
            Layout.fillWidth: true
            text: root.text
            role: "secondary"
            color: root.enabled
                ? MichiPalette.textPrimary : MichiPalette.textDisabled
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: MichiRadius.sm
        color: root.down ? MichiSemanticColors.surfacePressed
            : root.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
        HoverHandler { cursorShape: Qt.PointingHandCursor }
    }
}
