import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

FocusScope {
    id: root

    property string text: ""
    property string iconName: ""
    property string secondaryIconName: "chevron-down"
    property string accessibleName: text
    property string secondaryAccessibleName: qsTr("More options")
    property bool iconOnly: false
    readonly property real secondaryWidth: 28
    signal primaryClicked()
    signal secondaryClicked()

    implicitWidth: primaryButton.implicitWidth + secondaryButton.implicitWidth
    implicitHeight: MichiMetrics.controlMedium
    activeFocusOnTab: false

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.md
        color: MichiSemanticColors.controlSurface
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
        clip: true

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Button {
                id: primaryButton
                Layout.fillHeight: true
                Layout.fillWidth: true
                implicitWidth: root.iconOnly ? MichiMetrics.controlMedium
                    : Math.max(82, primaryContent.implicitWidth + MichiSpacing.lg * 2)
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Accessible.role: Accessible.Button
                Accessible.name: root.accessibleName
                onClicked: root.primaryClicked()

                contentItem: Row {
                    id: primaryContent
                    anchors.centerIn: parent
                    spacing: MichiSpacing.sm
                    MichiIcon {
                        name: root.iconName
                        width: MichiMetrics.iconSmall
                        height: width
                        iconColor: root.enabled
                            ? MichiPalette.textSecondary : MichiPalette.textDisabled
                    }
                    MichiText {
                        visible: !root.iconOnly
                        text: root.text
                        role: "secondary"
                        font.weight: Font.Medium
                        color: root.enabled
                            ? MichiPalette.textSecondary : MichiPalette.textDisabled
                    }
                }
                background: Rectangle {
                    color: primaryButton.pressed
                        ? MichiSemanticColors.surfacePressed
                        : primaryButton.hovered
                            ? MichiSemanticColors.surfaceHover : "transparent"
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: MichiSemanticColors.borderSubtle
            }

            Button {
                id: secondaryButton
                Layout.fillHeight: true
                Layout.preferredWidth: 28
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Accessible.role: Accessible.Button
                Accessible.name: root.secondaryAccessibleName
                onClicked: root.secondaryClicked()

                contentItem: MichiIcon {
                    anchors.centerIn: parent
                    name: root.secondaryIconName
                    width: 12
                    height: width
                    iconColor: root.enabled
                        ? MichiPalette.textSecondary : MichiPalette.textDisabled
                }
                background: Rectangle {
                    color: secondaryButton.pressed
                        ? MichiSemanticColors.surfacePressed
                        : secondaryButton.hovered
                            ? MichiSemanticColors.surfaceHover : "transparent"
                }
                MichiTooltip {
                    visible: secondaryButton.hovered
                    text: root.secondaryAccessibleName
                }
            }
        }

    }

    MichiFocusRing {
        visualFocus: primaryButton.visualFocus || secondaryButton.visualFocus
    }
}
