import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// AudioEnginePopup — quick engine selection ONLY (M11.3-UI).
// Simple, fast, no technical clutter. Full configuration lives in
// Settings > Audio Engine. Never shows DAC/DSD/sample-rate/buffer/
// pipeline information.
//
// M11.3-UI-R1: rows are REAL Buttons (focus + keyboard activation), the
// popup is LIVE-BOUND to the parent projections (never an imperative
// snapshot), and competing rows are disabled while a switch is in flight.
Popup {
    id: root
    // P1-03: explicit stable objectName for gate lookups (QML id is not
    // QObject.objectName).
    objectName: "AudioEnginePopup"

    property var engines: []
    property string selectedEngineId: ""
    property string activeEngineId: ""
    property string switchingTo: ""
    property string fallbackFrom: ""
    property bool hasFallback: false
    property string statusSummary: ""

    signal engineSwitchRequested(string engineId)

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: 320
    enter: Transition {
        // P2-01 (M11.3-UI-R2): no decorative fade under reduced motion;
        // open/close stay deterministic (instant) without animation.
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiMotion.panel }
    }
    exit: Transition {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiMotion.standard }
    }
    background: MichiGlassSurface {
        elevation: "elevated"
        contentPadding: 0
        tileSeed: 8
    }

    // Focus enters the popup predictably: first selectable engine row.
    onOpened: {
        for (var i = 0; i < engineRows.count; i++) {
            var item = engineRows.itemAt(i)
            if (item && item.enabled) {
                item.forceActiveFocus()
                break
            }
        }
    }

    // P2-02 (M11.3-UI-R2): Up/Down navigation SKIPS rows that are not
    // selectable (unavailable / disabled / mid-switch lock). No wrapping.
    function _navigate(fromIndex, delta) {
        var count = engineRows.count
        var i = fromIndex + delta
        while (i >= 0 && i < count) {
            var item = engineRows.itemAt(i)
            if (item !== null && item.enabled)
                return item
            i += delta
        }
        return null
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.xs

        MichiText {
            text: qsTr("Audio Engine")
            role: "heading"
            Layout.fillWidth: true
            Layout.bottomMargin: MichiSpacing.sm
        }

        // One-line fallback note (when preferred != active)
        MichiText {
            visible: root.hasFallback
            text: root.statusSummary
            role: "technical"
            technical: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            Layout.bottomMargin: MichiSpacing.xs
            color: MichiPalette.textSecondary
        }

        Repeater {
            id: engineRows
            model: root.engines
            delegate: Button {
                id: row
                required property var modelData
                required property int index
                objectName: "enginePopupRow_" + row.modelData.id
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                // The bridge owns the one live selection decision shared by
                // quick selection and Settings (including Stop & Switch).
                enabled: row.modelData.canSelectNow

                property bool isActive: row.modelData.id === root.activeEngineId
                property bool isSelected: row.modelData.id === root.selectedEngineId
                property bool isSwitching: row.modelData.id === root.switchingTo

                function statusLabel() {
                    if (row.isSwitching)
                        return qsTr("Switching\u2026")
                    if (row.isActive)
                        return qsTr("Active")
                    if (row.isSelected && root.hasFallback)
                        return qsTr("Preferred")
                    if (!row.modelData.canActivate)
                        return qsTr("Not available")
                    return ""
                }

                onClicked: root.engineSwitchRequested(row.modelData.id)
                // AbstractButton activates on Space only — add Return/Enter
                // (verified: no double activation with the built-in Space).
                Keys.onReturnPressed: row.clicked()
                Keys.onEnterPressed: row.clicked()
                // Up/Down navigation between ENABLED engine rows only
                // (disabled/unavailable rows are skipped; no wrapping).
                KeyNavigation.up: root._navigate(index, -1)
                KeyNavigation.down: root._navigate(index, 1)

                Accessible.name: row.modelData.displayName + " — " + row.statusLabel()
                Accessible.description: {
                    if (!row.modelData.canActivate)
                        return qsTr("Not available on this system")
                    if (row.modelData.selectionBlocker !== "")
                        return qsTr("Select ") + row.modelData.displayName
                            + " — " + row.modelData.selectionBlocker
                    return qsTr("Select ") + row.modelData.displayName
                }

                contentItem: RowLayout {
                    spacing: MichiSpacing.md

                    Rectangle {
                        Layout.preferredWidth: 12
                        Layout.preferredHeight: 12
                        radius: 6
                        color: row.isActive
                            ? MichiPalette.auroraCyan
                            : "transparent"
                        border.width: row.isActive ? 0 : 1
                        border.color: MichiPalette.textDisabled
                        visible: row.modelData.canActivate || row.isActive
                    }
                    MichiText {
                        text: row.modelData.displayName
                        role: "primary"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        color: row.isActive
                            ? MichiPalette.textPrimary
                            : MichiPalette.textSecondary
                    }
                    MichiText {
                        objectName: "enginePopupRowStatus_" + row.modelData.id
                        text: row.statusLabel()
                        role: "technical"
                        technical: true
                        color: row.isActive
                            ? MichiPalette.auroraCyan
                            : MichiPalette.textMuted
                    }
                }

                background: Rectangle {
                    radius: MichiRadius.sm
                    color: row.pressed
                        ? MichiSemanticColors.surfacePressed
                        : row.hovered ? MichiSemanticColors.surfaceHover
                        : "transparent"
                    border.width: row.visualFocus ? 1 : 0
                    border.color: MichiSemanticColors.focusRing
                }
            }
        }
    }
}
