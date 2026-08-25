import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// AudioEngineSettingsSection — complete but understandable Audio Engine
// configuration surface (M11.3-UI). Explains what an audio engine is,
// shows Preferred vs In use truthfully, exposes engine cards with plain
// language, and discloses technical details progressively. Engine != DAC.
Item {
    id: root

    property var engines: []
    property string selectedEngineId: ""
    property string activeEngineId: ""
    property string lifecycleLabel: ""
    property string fallbackFrom: ""
    property string errorMessage: ""
    property string statusSummary: ""

    signal engineSwitchRequested(string engineId)

    implicitHeight: content.implicitHeight + MichiTheme.space16 + MichiTheme.space16

    MichiGlassSurface {
        id: enginePanel
        objectName: "audioEngineSettingsPanel"
        anchors.fill: parent

        ColumnLayout {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: MichiTheme.space12

            Text {
                text: qsTr("Audio Engine")
                font.pixelSize: MichiTheme.fontSizeTitle
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.textPrimary
                Accessible.role: Accessible.Heading
            }

            Text {
                text: qsTr(
                    "Choose how Michi runs audio playback. "
                    + "This is separate from the audio device or DAC."
                )
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.textSecondary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Accessible.role: Accessible.StaticText
            }

            // ── Preferred vs In use (truthful, never collapsed) ────────
            RowLayout {
                Layout.topMargin: MichiTheme.space4
                spacing: MichiTheme.space24

                ColumnLayout {
                    spacing: MichiTheme.space2
                    Text {
                        text: qsTr("Preferred")
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textMuted
                    }
                    Text {
                        text: root._nameOf(root.selectedEngineId)
                        font.pixelSize: MichiTheme.fontSizeBody
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }
                }
                ColumnLayout {
                    spacing: MichiTheme.space2
                    Text {
                        text: qsTr("In use")
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textMuted
                    }
                    Text {
                        text: root.activeEngineId === ""
                            ? qsTr("None")
                            : root._nameOf(root.activeEngineId)
                        font.pixelSize: MichiTheme.fontSizeBody
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                    }
                }
                ColumnLayout {
                    spacing: MichiTheme.space2
                    Text {
                        text: qsTr("Status")
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textMuted
                    }
                    Text {
                        text: root.lifecycleLabel
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textPrimary
                    }
                }
            }

            // ── Fallback explanation (when preferred != active) ────────
            Rectangle {
                visible: root.fallbackFrom !== ""
                    && root.selectedEngineId !== root.activeEngineId
                Layout.fillWidth: true
                radius: MichiRadius.md
                color: MichiSemanticColors.surfaceSoft
                border.width: 1
                border.color: MichiSemanticColors.borderSubtle
                Layout.topMargin: MichiTheme.space4

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.space12
                    spacing: MichiTheme.space4
                    Text {
                        text: root.statusSummary
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textPrimary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        Accessible.role: Accessible.StaticText
                    }
                    Text {
                        visible: root.errorMessage !== ""
                        text: root.errorMessage
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            // ── Engine cards (plain language, truthful) ────────────────
            Repeater {
                model: root.engines
                delegate: Rectangle {
                    id: card
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.topMargin: MichiTheme.space4
                    radius: MichiRadius.md
                    color: card.modelData.selected
                        ? MichiSemanticColors.surfaceSoft
                        : MichiSemanticColors.surfaceSoft
                    border.width: card.modelData.selected ? 1 : 0
                    border.color: card.modelData.selected
                        ? MichiSemanticColors.borderStrong
                        : "transparent"

                    property bool isActive: card.modelData.id === root.activeEngineId
                    property bool isSelected: card.modelData.id === root.selectedEngineId

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.space12
                        spacing: MichiTheme.space4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.space8
                            Text {
                                text: card.modelData.displayName
                                font.pixelSize: MichiTheme.fontSizeBody
                                font.weight: MichiTheme.fontWeightBold
                                color: MichiTheme.textPrimary
                            }
                            Text {
                                text: "· " + card.modelData.shortIdentity
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textMuted
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: card.statusText()
                                font.pixelSize: MichiTheme.fontSizeBody
                                font.weight: MichiTheme.fontWeightBold
                                color: card.isActive
                                    ? MichiSemanticColors.auroraCyan
                                    : MichiPalette.textSecondary
                                Accessible.role: Accessible.StaticText
                            }
                        }

                        Text {
                            text: card.modelData.description
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiTheme.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Text {
                            visible: !card.modelData.canActivate
                            text: qsTr("Michi cannot use %1 on this system.")
                                .arg(card.modelData.displayName)
                            font.pixelSize: MichiTheme.fontSizeBody
                            color: MichiPalette.textSecondary
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        function statusText() {
                            if (card.isActive && card.isSelected)
                                return qsTr("Preferred · In use")
                            if (card.isActive)
                                return qsTr("In use")
                            if (card.isSelected)
                                return qsTr("Preferred")
                            if (!card.modelData.canActivate)
                                return qsTr("Not available")
                            return ""
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: card.modelData.canActivate
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.engineSwitchRequested(card.modelData.id)
                            Accessible.role: Accessible.Button
                            Accessible.name: qsTr("Select ") + card.modelData.displayName
                            Accessible.onPressAction: root.engineSwitchRequested(
                                card.modelData.id
                            )
                        }
                    }
                }
            }

            // ── Advanced engine details (progressive disclosure) ───────
            ColumnLayout {
                Layout.topMargin: MichiTheme.space8
                spacing: MichiTheme.space8
                property bool expanded: false

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 34
                    radius: MichiRadius.md
                    color: "transparent"

                    Text {
                        text: advanced.expanded ? qsTr("Hide advanced engine details")
                            : qsTr("Advanced engine details")
                        anchors.centerIn: parent
                        font.pixelSize: MichiTheme.fontSizeBody
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiPalette.textSecondary
                        Accessible.role: Accessible.Button
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: advanced.expanded = !advanced.expanded
                    }
                }

                ColumnLayout {
                    id: advanced
                    visible: advanced.expanded
                    spacing: MichiTheme.space4
                    Layout.fillWidth: true

                    Repeater {
                        model: root.engines
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: MichiTheme.space2

                            Text {
                                text: modelData.displayName
                                font.pixelSize: MichiTheme.fontSizeBody
                                font.weight: MichiTheme.fontWeightBold
                                color: MichiTheme.textPrimary
                            }
                            Text {
                                text: qsTr("Engine ID: %1").arg(modelData.id)
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textSecondary
                            }
                            Text {
                                text: qsTr("Available: %1 · Implemented: %2")
                                    .arg(modelData.available ? qsTr("Yes") : qsTr("No"))
                                    .arg(modelData.implemented ? qsTr("Yes") : qsTr("No"))
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textSecondary
                            }
                            Text {
                                visible: modelData.activationBlocker !== ""
                                    && modelData.activationBlocker !== undefined
                                text: qsTr("Technical reason: %1")
                                    .arg(modelData.activationBlocker)
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            Text {
                                text: qsTr("Transport capabilities: %1")
                                    .arg(root._capabilityText(modelData.capabilities))
                                font.pixelSize: MichiTheme.fontSizeBody
                                color: MichiTheme.textSecondary
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            // ── Engine configuration note (truthful, no fake knobs) ────
            Text {
                visible: root._noTunables
                Layout.topMargin: MichiTheme.space8
                text: qsTr(
                    "Engine configuration is managed automatically by Michi."
                )
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.textSecondary
            }
        }
    }

    property bool _noTunables: true  // M11.3 exposes no user-engine tunables

    function _nameOf(engineId) {
        for (var i = 0; i < root.engines.length; i++) {
            if (root.engines[i].id === engineId)
                return root.engines[i].displayName
        }
        return engineId
    }

    function _capabilityText(caps) {
        if (!caps) return ""
        var labels = []
        if (caps.localFilePlayback) labels.push(qsTr("Local playback"))
        if (caps.seek) labels.push(qsTr("Seek"))
        if (caps.pause) labels.push(qsTr("Pause"))
        if (caps.volume) labels.push(qsTr("Volume"))
        if (caps.mute) labels.push(qsTr("Mute"))
        return labels.join(", ")
    }
}
