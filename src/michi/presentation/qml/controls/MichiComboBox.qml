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
    indicator: MichiText {
        x: root.width - width - MichiSpacing.md
        y: root.topPadding + (root.availableHeight - height) / 2
        text: "⌄"
        role: "secondary"
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
        background: Rectangle { color: option.highlighted ? MichiSemanticColors.surfaceSelected : "transparent"; radius: MichiRadius.sm }
    }
    popup: Popup {
        y: root.height + MichiSpacing.xs
        width: root.width
        implicitHeight: contentItem.implicitHeight + MichiSpacing.sm * 2
        padding: MichiSpacing.xs
        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 260)
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
        }
        background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0 }
    }
}
