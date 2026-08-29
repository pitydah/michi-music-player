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
    readonly property bool hasPrimaryIcon: iconName.length > 0
    readonly property real secondaryWidth: 26
    readonly property real secondaryIconSize: 10
    signal primaryClicked()
    signal secondaryClicked()

    // Explicit segment math: the icon (16 px) + its spacing (8 px) must
    // always widen the primary segment — positioner implicit sizes never
    // drive this (a hidden→visible icon must never be a ghost reservation
    // nor silently collapse the segment).
    readonly property real textWidth: primaryLabel.contentWidth
    readonly property real primarySegmentImplicitWidth:
        root.iconOnly && root.hasPrimaryIcon
            ? MichiMetrics.controlMedium
            : Math.max(82,
                root.textWidth
                    + (root.hasPrimaryIcon
                        ? MichiMetrics.iconSmall + MichiSpacing.sm : 0)
                    + MichiSpacing.md * 2)

    implicitWidth: root.primarySegmentImplicitWidth + root.secondaryWidth + 1
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
                implicitWidth: root.primarySegmentImplicitWidth
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
                        visible: root.hasPrimaryIcon
                        width: MichiMetrics.iconSmall
                        height: width
                        iconColor: root.enabled
                            ? MichiPalette.textSecondary : MichiPalette.textDisabled
                    }
                    MichiText {
                        id: primaryLabel
                        // An icon-less instance must never collapse to a
                        // blank primary segment when a responsive caller
                        // requests icon-only presentation.
                        visible: !root.iconOnly || !root.hasPrimaryIcon
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

            Item {
                id: segmentDivider
                Layout.fillHeight: true
                Layout.preferredWidth: 1

                Rectangle {
                    id: dividerLine
                    anchors.centerIn: parent
                    width: 1
                    height: MichiMetrics.iconSmall
                    color: MichiSemanticColors.borderSubtle
                }
            }

            Button {
                id: secondaryButton
                Layout.fillHeight: true
                Layout.preferredWidth: root.secondaryWidth
                implicitWidth: root.secondaryWidth
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                Accessible.role: Accessible.Button
                Accessible.name: root.secondaryAccessibleName
                onClicked: root.secondaryClicked()

                contentItem: MichiIcon {
                    anchors.centerIn: parent
                    name: root.secondaryIconName
                    width: root.secondaryIconSize
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
