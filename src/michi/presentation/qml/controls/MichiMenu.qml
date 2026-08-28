import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Menu {
    id: root
    padding: MichiSpacing.xs
    implicitWidth: 284
    // Consistent with the popup family: fade + subtle slide, outCubic
    enter: Transition {
        NumberAnimation {
            property: "opacity"; from: 0; to: 1
            duration: MichiMotion.panel
            easing.type: MichiMotion.outCubic
        }
        NumberAnimation {
            property: "y"; from: -6; to: 0
            duration: MichiMotion.panel
            easing.type: MichiMotion.outCubic
        }
    }
    exit: Transition {
        NumberAnimation {
            property: "opacity"; from: 1; to: 0
            duration: MichiMotion.standard
            easing.type: MichiMotion.outCubic
        }
    }
    delegate: MenuItem {
        id: menuItem
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
                    visible: menuItem.icon.name.length > 0
                    name: menuItem.icon.name
                    iconColor: menuItem.enabled
                        ? MichiPalette.textPrimary : MichiPalette.textDisabled
                }
                MichiText {
                    anchors.centerIn: parent
                    visible: menuItem.checkable && menuItem.icon.name.length === 0
                    text: menuItem.checked ? "✓" : ""
                    role: "technical"
                    technical: true
                    color: MichiPalette.auroraCyan
                }
            }
            MichiText {
                Layout.fillWidth: true
                text: menuItem.text
                role: "secondary"
                color: menuItem.enabled
                    ? MichiPalette.textPrimary : MichiPalette.textDisabled
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            radius: MichiRadius.sm
            color: menuItem.down ? MichiSemanticColors.surfacePressed
                : menuItem.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
    }
    background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.md; tileSeed: 9 }
}
