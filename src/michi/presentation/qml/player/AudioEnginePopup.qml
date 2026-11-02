import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../controls"
import "../primitives"
import "../theme"

// AudioEnginePopup — quick backend selection (F11).
// One question: which audio engine is playing? Rows expose selection and
// active state separately; all runtime policy still belongs to the bridge.
Popup {
    id: root
    objectName: "AudioEnginePopup"

    property var engines: []
    property string selectedEngineId: ""
    property string activeEngineId: ""
    property string switchingTo: ""
    property string fallbackFrom: ""
    property bool hasFallback: false
    property string statusSummary: ""
    property bool engineSwitchReady: true
    property string engineSwitchBlocker: ""
    property var focusReturnTarget: null

    signal engineSwitchRequested(string engineId)

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: Math.max(320, Math.min(360, (Overlay.overlay
        ? Overlay.overlay.width : 360) - 24))
    enter: Transition {
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
        materialOpacityOverride: 1.0
    }

    onOpened: {
        for (var i = 0; i < engineRows.count; i++) {
            var item = engineRows.itemAt(i)
            if (item && item.enabled) {
                item.forceActiveFocus()
                break
            }
        }
    }
    onClosed: {
        if (root.focusReturnTarget)
            root.focusReturnTarget.forceActiveFocus()
    }

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
        spacing: MichiSpacing.sm

        MichiPopupHeader {
            Layout.fillWidth: true
            iconName: "audio-engine"
            title: qsTr("Audio Engine")
            subtitle: qsTr("Choose the backend that plays your music")
        }

        MichiText {
            visible: root.statusSummary.length > 0
            text: root.statusSummary
            role: "secondary"
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
                Layout.preferredHeight: 56
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                enabled: row.modelData.selectionAllowed
                    && row.modelData.selectionAction !== "noop"
                    && !row.isSwitching

                property bool isActive: row.modelData.id === root.activeEngineId
                property bool isSelected: row.modelData.id === root.selectedEngineId
                property bool isSwitching: row.modelData.switching

                function statusLabel() {
                    if (row.isSwitching)
                        return qsTr("Switching\u2026")
                    if (row.isActive)
                        return qsTr("Active")
                    if (row.isSelected && root.hasFallback)
                        return qsTr("Preferred")
                    if (!row.modelData.canActivate)
                        return qsTr("Not available")
                    if (!row.modelData.selectionAllowed
                            && row.modelData.selectionBlocker)
                        return qsTr("Switch blocked — %1")
                            .arg(row.modelData.selectionBlocker)
                    return ""
                }

                onClicked: root.engineSwitchRequested(row.modelData.id)
                Keys.onReturnPressed: row.clicked()
                Keys.onEnterPressed: row.clicked()
                KeyNavigation.up: root._navigate(index, -1)
                KeyNavigation.down: root._navigate(index, 1)

                Accessible.name: row.modelData.displayName + " — " + row.statusLabel()
                Accessible.description: {
                    if (!row.modelData.canActivate)
                        return qsTr("Not available on this system")
                    if (!row.modelData.selectionAllowed
                            && row.modelData.selectionBlocker !== "")
                        return qsTr("Select ") + row.modelData.displayName
                            + " — " + row.modelData.selectionBlocker
                    if (row.isSwitching)
                        return qsTr("Select ") + row.modelData.displayName
                            + " — " + qsTr("Audio engine change is already in progress.")
                    return qsTr("Select ") + row.modelData.displayName
                }

                contentItem: RowLayout {
                    spacing: MichiSpacing.md

                    // Selection intent (separate from the Active badge).
                    Rectangle {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        radius: 8
                        color: "transparent"
                        border.width: row.isSelected ? 5 : 1
                        border.color: row.isSelected
                            ? MichiPalette.auroraBlue
                            : MichiPalette.textDisabled
                        opacity: row.modelData.canActivate || row.isActive ? 1 : 0.45
                    }

                    MichiIcon {
                        name: row.modelData.iconType || "audio-engine"
                        width: MichiMetrics.iconMedium
                        height: width
                        strokeWidth: 1.7
                        iconColor: row.isActive
                            ? MichiPalette.auroraCyan
                            : row.modelData.canActivate
                                ? MichiPalette.textSecondary
                                : MichiPalette.textDisabled
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        MichiText {
                            text: row.modelData.displayName
                            role: "body"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            color: row.isActive
                                ? MichiPalette.textPrimary
                                : row.modelData.canActivate
                                    ? MichiPalette.textPrimary
                                    : MichiPalette.textMuted
                        }
                        MichiText {
                            text: row.modelData.quickSubtitle || row.modelData.shortIdentity
                            role: "caption"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            color: MichiPalette.textMuted
                        }
                    }

                    MichiStatusChip {
                        visible: row.isActive
                        text: qsTr("Active")
                        tone: "active"
                    }

                    MichiText {
                        objectName: "enginePopupRowStatus_" + row.modelData.id
                        text: row.statusLabel()
                        role: "technical"
                        technical: true
                        visible: text.length > 0 && !row.isActive
                        color: row.isSwitching
                            ? MichiPalette.auroraCyan
                            : row.modelData.canActivate
                                ? MichiPalette.textMuted
                                : MichiPalette.warning
                    }
                }

                background: Rectangle {
                    radius: MichiRadius.md
                    color: row.pressed
                        ? MichiSemanticColors.surfacePressed
                        : row.hovered ? MichiSemanticColors.surfaceHover
                        : row.isSelected ? MichiSemanticColors.surfaceSelected
                        : "transparent"
                    border.width: row.visualFocus ? 1
                        : row.isSelected ? 1 : 0
                    border.color: row.visualFocus
                        ? MichiSemanticColors.focusRing
                        : MichiSemanticColors.borderSubtle
                    MichiFocusRing { visualFocus: row.visualFocus }
                }
            }
        }
    }
}
