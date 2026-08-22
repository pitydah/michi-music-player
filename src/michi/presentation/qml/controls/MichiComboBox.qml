import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

ComboBox {
    id: root
    property string accessibleName: "Options"
    implicitHeight: MichiMetrics.controlMedium
    leftPadding: MichiSpacing.md
    rightPadding: MichiSpacing.xl
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.ComboBox
    Accessible.name: accessibleName
    contentItem: MichiText {
        leftPadding: 0
        rightPadding: root.indicator.width + root.spacing
        text: root.displayText
        role: "secondary"
        color: root.enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: MichiIcon {
        x: root.width - width - MichiSpacing.md
        y: root.topPadding + (root.availableHeight - height) / 2
        width: MichiMetrics.iconSmall
        height: width
        name: "chevron-down"
        iconColor: !root.enabled ? MichiPalette.textDisabled
            : root.pressed || root.visualFocus ? MichiPalette.auroraCyan
            : root.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
        Behavior on iconColor {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }
    background: Rectangle {
        radius: MichiRadius.md
        color: root.pressed ? MichiSemanticColors.surfacePressed : MichiSemanticColors.controlSurface
        border.width: root.visualFocus ? 2 : 1
        border.color: root.visualFocus ? MichiPalette.auroraBlue : MichiSemanticColors.borderSubtle
    }
    delegate: ItemDelegate {
        id: option
        required property int index
        required property var modelData
        width: ListView.view.width
        text: modelData
        highlighted: root.highlightedIndex === index
        contentItem: MichiText { text: option.text; role: "secondary"; color: option.highlighted ? MichiPalette.textPrimary : MichiPalette.textSecondary }
        background: Rectangle {
            radius: MichiRadius.sm
            color: option.down ? MichiSemanticColors.surfacePressed
                : option.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
    }
    popup: Popup {
        y: root.height + MichiSpacing.xs
        width: root.width
        implicitHeight: contentItem.implicitHeight + MichiSpacing.sm * 2
        padding: MichiSpacing.xs
        focus: true
        enter: Transition {
            NumberAnimation {
                property: "opacity"; from: 0; to: 1
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
        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 260)
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
        }
        background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.md }
    }
}
