pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

ComboBox {
    id: root
    property string accessibleName: "Options"
    property string enabledRole: ""
    property int keyboardIndex: -1
    readonly property bool popupVisible: popup.visible
    function optionEnabled(index) {
        if (root.enabledRole === "")
            return true
        var item = root.model && index >= 0 ? root.model[index] : null
        return item !== null && item[root.enabledRole] !== false
    }
    function nextEnabledIndex(fromIndex, delta) {
        var index = fromIndex + delta
        while (index >= 0 && index < root.count) {
            if (root.optionEnabled(index))
                return index
            index += delta
        }
        return fromIndex
    }
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
        objectName: root.objectName + "_option_" + index
        width: ListView.view.width
        text: root.textAt(index)
        enabled: root.optionEnabled(index)
        opacity: enabled ? 1 : 0.55
        highlighted: option.hovered || root.keyboardIndex === index
        Keys.onDownPressed: event => {
            optionList.focusEnabled(index, 1)
            event.accepted = true
        }
        Keys.onUpPressed: event => {
            optionList.focusEnabled(index, -1)
            event.accepted = true
        }
        Keys.onReturnPressed: event => {
            root.activated(index)
            comboPopup.close()
            event.accepted = true
        }
        Keys.onEnterPressed: event => {
            root.activated(index)
            comboPopup.close()
            event.accepted = true
        }
        Keys.onEscapePressed: event => {
            comboPopup.close()
            event.accepted = true
        }
        contentItem: MichiText { text: option.text; role: "secondary"; color: option.highlighted ? MichiPalette.textPrimary : MichiPalette.textSecondary }
        background: Rectangle {
            radius: MichiRadius.sm
            color: option.down ? MichiSemanticColors.surfacePressed
                : option.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
    }
    popup: Popup {
        id: comboPopup
        y: root.height + MichiSpacing.xs
        width: root.width
        implicitHeight: contentItem.implicitHeight + MichiSpacing.sm * 2
        padding: MichiSpacing.xs
        focus: true
        onOpened: {
            root.keyboardIndex = root.currentIndex
            Qt.callLater(function() {
                optionList.focusEnabled(root.currentIndex, 0)
            })
        }
        onClosed: root.forceActiveFocus()
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
            id: optionList
            clip: true
            focus: true
            implicitHeight: Math.min(contentHeight, 260)
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.keyboardIndex
            function focusEnabled(fromIndex, delta) {
                var targetIndex = delta === 0
                    ? fromIndex : root.nextEnabledIndex(fromIndex, delta)
                if (!root.optionEnabled(targetIndex))
                    targetIndex = root.nextEnabledIndex(targetIndex, delta || 1)
                var item = optionList.itemAtIndex(targetIndex)
                if (item && item.enabled) {
                    root.keyboardIndex = targetIndex
                    item.forceActiveFocus()
                }
            }
        }
        background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.md }
    }
    Shortcut {
        sequence: "Escape"
        context: Qt.WindowShortcut
        enabled: comboPopup.visible
        onActivated: comboPopup.close()
    }
}
