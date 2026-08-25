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
Popup {
    id: root

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
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiMotion.panel }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiMotion.standard }
    }
    background: MichiGlassSurface {
        elevation: "elevated"
        contentPadding: 0
        tileSeed: 8
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
            model: root.engines
            delegate: RowLayout {
                id: row
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                spacing: MichiSpacing.md

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

                Rectangle {
                    Layout.preferredWidth: 12
                    Layout.preferredHeight: 12
                    radius: 6
                    color: row.isActive
                        ? MichiSemanticColors.auroraCyan
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
                    Accessible.role: Accessible.StaticText
                    Accessible.name: row.modelData.displayName + " — " + row.statusLabel()
                }
                MichiText {
                    text: row.statusLabel()
                    role: "technical"
                    technical: true
                    color: row.isActive
                        ? MichiSemanticColors.auroraCyan
                        : MichiPalette.textMuted
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: row.modelData.canActivate && !row.isSwitching
                    hoverEnabled: true
                    onClicked: root.engineSwitchRequested(row.modelData.id)
                    Accessible.role: Accessible.Button
                    Accessible.name: qsTr("Select ") + row.modelData.displayName
                    Accessible.onPressAction: root.engineSwitchRequested(
                        row.modelData.id
                    )
                    cursorShape: Qt.PointingHandCursor
                }
                Keys.onReturnPressed: root.engineSwitchRequested(row.modelData.id)
                Keys.onEnterPressed: root.engineSwitchRequested(row.modelData.id)
            }
        }
    }
}
