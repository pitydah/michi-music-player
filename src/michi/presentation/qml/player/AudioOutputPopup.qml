pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root
    objectName: "AudioOutputPopup"
    property var devices: []
    property string signalTruthLabel: qsTr("Not verified")
    property string failureTitle: ""
    property var focusReturnTarget: null

    signal deviceSelectionRequested(string stableDeviceId)
    signal sharedSelectionRequested()
    signal settingsRequested()

    padding: MichiSpacing.lg
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: 360
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

    contentItem: ColumnLayout {
        spacing: MichiSpacing.sm
        MichiText {
            text: qsTr("Audio Output")
            role: "heading"
            Layout.fillWidth: true
        }

        Repeater {
            id: outputRows
            objectName: "audioOutputPopupRepeater"
            model: root.devices
            delegate: Button {
                id: row
                required property var modelData
                required property int index
                objectName: "outputPopupRow_" + (modelData.stableDeviceId || "shared")
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                focusPolicy: Qt.StrongFocus
                hoverEnabled: true
                enabled: modelData.canSelect
                onClicked: {
                    if (row.modelData.isShared)
                        root.sharedSelectionRequested()
                    else
                        root.deviceSelectionRequested(row.modelData.stableDeviceId)
                }
                Keys.onReturnPressed: row.clicked()
                Keys.onEnterPressed: row.clicked()
                KeyNavigation.up: root.navigate(index, -1)
                KeyNavigation.down: root.navigate(index, 1)
                Accessible.name: row.modelData.displayName + " — "
                    + row.modelData.statusLabel
                Accessible.description: row.modelData.transportLabel + " · "
                    + row.modelData.signalTruthLabel

                contentItem: RowLayout {
                    spacing: MichiSpacing.sm
                    Rectangle {
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 10
                        radius: 5
                        color: row.modelData.active ? MichiPalette.auroraCyan : "transparent"
                        border.width: row.modelData.active ? 0 : 1
                        border.color: row.modelData.available
                            ? MichiPalette.textMuted : MichiPalette.warning
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        MichiText {
                            Layout.fillWidth: true
                            text: row.modelData.displayName
                            role: "primary"
                            elide: Text.ElideRight
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: row.modelData.statusLabel + " · "
                                + row.modelData.transportLabel
                            role: "technical"
                            technical: true
                            elide: Text.ElideRight
                        }
                    }
                    MichiText {
                        visible: row.modelData.active
                        text: row.modelData.signalTruthLabel
                        role: "technical"
                        technical: true
                    }
                }
                background: Rectangle {
                    radius: MichiRadius.sm
                    color: row.pressed ? MichiSemanticColors.surfacePressed
                        : row.hovered ? MichiSemanticColors.surfaceHover : "transparent"
                    border.width: row.visualFocus || row.modelData.selected ? 1 : 0
                    border.color: row.visualFocus
                        ? MichiSemanticColors.focusRing : MichiSemanticColors.borderStrong
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

        MichiButton {
            objectName: "openAudioOutputSettingsButton"
            Layout.fillWidth: true
            text: qsTr("Audio Output Settings")
            variant: "secondary"
            onClicked: root.settingsRequested()
        }
    }
}
