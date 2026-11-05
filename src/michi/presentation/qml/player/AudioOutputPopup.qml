pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root
    objectName: "AudioOutputPopup"
    property var devices: []
    property var deviceGroups: []
    property string signalTruthLabel: qsTr("Not verified")
    property string failureTitle: ""
    property var recoveryActions: []
    property var focusReturnTarget: null
    property bool displayAudioExpanded: false
    property real maximumRowsHeight: Math.max(
        160, Math.min(420, (Overlay.overlay ? Overlay.overlay.height : 560) - 160)
    )

    signal deviceSelectionRequested(string stableDeviceId)
    signal sharedSelectionRequested()
    signal settingsRequested()
    signal recoveryActionRequested(string action)

    padding: MichiSpacing.lg
    margins: MichiSpacing.sm
    modal: true
    dim: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: Math.max(340, Math.min(380,
        (Overlay.overlay ? Overlay.overlay.width : 420) - 24))
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
        tileSeed: 11
        materialOpacityOverride: 1.0
    }

    function groups() {
        if (root.deviceGroups && root.deviceGroups.length > 0)
            return root.deviceGroups
        return [{"groupId": "legacy", "label": "", "collapsedByDefault": false, "rows": root.devices}]
    }

    function visibleRows() {
        var rows = []
        var source = root.groups()
        for (var g = 0; g < source.length; ++g) {
            var group = source[g]
            var groupRows = group.rows || []
            if (group.groupId === "system") {
                for (var s = 0; s < groupRows.length; ++s)
                    rows.push(groupRows[s])
                continue
            }
            if (group.groupId === "display") {
                rows.push({
                    "isGroupHeader": true,
                    "stableDeviceId": "__display_audio__",
                    "displayName": group.label || qsTr("Display Audio"),
                    "statusLabel": qsTr("%1 output(s) · %2").arg(groupRows.length).arg(root.displayAudioExpanded ? qsTr("Collapse") : qsTr("Expand")),
                    "transportLabel": qsTr("HDMI / DisplayPort"),
                    "available": true,
                    "active": false,
                    "selected": false,
                    "canSelect": true,
                    "signalTruthLabel": ""
                })
                if (!root.displayAudioExpanded)
                    continue
            } else if ((group.label || "") !== "") {
                rows.push({
                    "isGroupHeader": true,
                    "stableDeviceId": "__header_" + group.groupId,
                    "displayName": group.label,
                    "statusLabel": group.description || "",
                    "transportLabel": "",
                    "available": true,
                    "active": false,
                    "selected": false,
                    "canSelect": false,
                    "signalTruthLabel": ""
                })
            }
            for (var i = 0; i < groupRows.length; ++i)
                rows.push(groupRows[i])
        }
        return rows
    }

    onOpened: {
        for (var i = 0; i < outputRows.count; i++) {
            var item = outputRows.itemAt(i)
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

    function navigate(fromIndex, delta) {
        var i = fromIndex + delta
        while (i >= 0 && i < outputRows.count) {
            var item = outputRows.itemAt(i)
            if (item && item.enabled)
                return item
            i += delta
        }
        return null
    }

    function activeStatusText() {
        for (var i = 0; i < root.devices.length; ++i) {
            if (root.devices[i].active)
                return root.devices[i].quickStatus || root.devices[i].activeLabel || "Active"
        }
        return ""
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.sm
        MichiPopupHeader {
            Layout.fillWidth: true
            routeIconName: "dac"
            title: qsTr("Audio Output")
            subtitle: qsTr("Choose where Michi plays")
            badgeText: root.activeStatusText()
            badgeTone: "active"
        }

        ScrollView {
            id: outputRowsScroll
            objectName: "outputRowsScroll"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(outputRowsColumn.implicitHeight, root.maximumRowsHeight)
            Layout.maximumHeight: root.maximumRowsHeight
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                id: outputRowsColumn
                width: outputRowsScroll.availableWidth
                Repeater {
                    id: outputRows
            objectName: "audioOutputPopupRepeater"
            model: root.visibleRows()
            delegate: Button {
                id: row
                required property var modelData
                required property int index
                objectName: "outputPopupRow_" + (modelData.stableDeviceId || "shared")
                Layout.fillWidth: true
                Layout.preferredHeight: modelData.isGroupHeader ? 34 : 66
                focusPolicy: modelData.isGroupHeader && modelData.stableDeviceId !== "__display_audio__"
                    ? Qt.NoFocus : Qt.StrongFocus
                hoverEnabled: true
                enabled: modelData.canSelect
                onClicked: {
                    if (row.modelData.isGroupHeader) {
                        if (row.modelData.stableDeviceId === "__display_audio__")
                            root.displayAudioExpanded = !root.displayAudioExpanded
                    } else if (row.modelData.isShared) {
                        root.sharedSelectionRequested()
                    } else {
                        root.deviceSelectionRequested(row.modelData.stableDeviceId)
                    }
                }
                Keys.onReturnPressed: row.clicked()
                Keys.onEnterPressed: row.clicked()
                KeyNavigation.up: root.navigate(index, -1)
                KeyNavigation.down: root.navigate(index, 1)
                Accessible.name: row.modelData.displayName + " — "
                    + row.modelData.statusLabel
                    + (row.modelData.pending && row.modelData.pendingReason
                        ? " · " + row.modelData.pendingReason : "")
                Accessible.description: row.modelData.isGroupHeader
                    ? (row.modelData.stableDeviceId === "__display_audio__"
                        ? qsTr("Toggle display audio outputs") : qsTr("Output category"))
                    : (row.modelData.quickSubtitle || row.modelData.transportLabel || "")
                readonly property string routeIcon:
                    row.modelData.iconType
                    || (row.modelData.isShared ? "system" : "generic")

                contentItem: RowLayout {
                    spacing: MichiSpacing.md
                    Rectangle {
                        visible: !row.modelData.isGroupHeader
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        radius: 7
                        color: "transparent"
                        border.width: 1
                        border.color: row.modelData.selected
                            ? MichiPalette.auroraBlue : MichiPalette.textMuted
                        Rectangle {
                            anchors.centerIn: parent
                            width: 6
                            height: 6
                            radius: 3
                            visible: row.modelData.selected
                            color: MichiPalette.auroraBlue
                        }
                    }
                    Rectangle {
                        visible: !row.modelData.isGroupHeader
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        radius: 9
                        color: row.modelData.active ? MichiSemanticColors.auroraCyanSurface
                            : MichiPalette.trackSurfaceBottom
                        border.width: 1
                        border.color: row.modelData.active ? MichiSemanticColors.auroraCyanBorderSubtle
                            : MichiSemanticColors.borderSubtle
                        MichiAudioRouteIcon {
                            anchors.centerIn: parent
                            width: 24
                            height: 24
                            roleName: row.routeIcon
                            iconColor: row.modelData.active ? MichiPalette.auroraCyan
                                : row.modelData.available
                                    ? MichiPalette.textSecondary
                                    : MichiPalette.textDisabled
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        MichiText {
                            Layout.fillWidth: true
                            text: row.modelData.displayName
                            role: row.modelData.isGroupHeader ? "secondary" : "body"
                            font.weight: row.modelData.isGroupHeader ? Font.DemiBold : Font.Normal
                            elide: Text.ElideRight
                        }
                        MichiText {
                            visible: !row.modelData.isGroupHeader
                            Layout.fillWidth: true
                            text: row.modelData.pending
                                ? (row.modelData.pendingReason || qsTr("Preparing…"))
                                : (row.modelData.quickSubtitle
                                    || row.modelData.statusLabel
                                    || row.modelData.transportLabel || "")
                            role: "technical"
                            technical: true
                            elide: Text.ElideRight
                            color: row.modelData.pending
                                ? MichiPalette.warning : MichiPalette.textSecondary
                        }
                    }
                    MichiStatusChip {
                        visible: !row.modelData.isGroupHeader && row.modelData.active
                        text: row.modelData.quickStatus
                            || row.modelData.activeLabel || qsTr("Active")
                        tone: "active"
                    }
                    MichiText {
                        visible: row.modelData.stableDeviceId === "__display_audio__"
                        text: root.displayAudioExpanded ? "▾" : "›"
                        role: "secondary"
                    }
                }
                background: MichiRouteSelectionSkin {
                    selected: !row.modelData.isGroupHeader && row.modelData.selected
                    active: !row.modelData.isGroupHeader && row.modelData.active
                    hovered: row.hovered && row.enabled
                    pressed: row.pressed
                    visualFocus: row.visualFocus
                    available: row.modelData.available
                    // Headers are section labels, except Display Audio's real toggle.
                    opacity: row.modelData.isGroupHeader ? 0.34 : 1.0
                }
            }
        }
            }
        }

        MichiText {
            visible: root.failureTitle !== ""
            Layout.fillWidth: true
            text: root.failureTitle
            role: "secondary"
            wrapMode: Text.WordWrap
        }

        // The normal surface must offer the same recovery the settings surface
        // offers: a typed refusal carries its explicit intents with it, so the
        // user never has to navigate away to resolve it. Nothing here switches
        // policy on its own - every row is a real user intent.
        Repeater {
            objectName: "outputRecoveryActionRepeater"
            model: root.failureTitle !== "" ? (root.recoveryActions || []) : []
            delegate: MichiButton {
                required property var modelData
                objectName: "outputRecoveryAction_" + (modelData.action || "unknown")
                Layout.fillWidth: true
                text: modelData.label || modelData.action || ""
                variant: modelData.action === "try_compatible_direct" ? "primary" : "secondary"
                onClicked: root.recoveryActionRequested(modelData.action)
            }
        }

        MichiButton {
            objectName: "openAudioOutputSettingsButton"
            Layout.fillWidth: true
            text: qsTr("Audio Output Settings")
            iconName: "settings"
            variant: "secondary"
            accessibleName: qsTr("Open detailed audio output settings")
            onClicked: root.settingsRequested()
        }
    }
}
