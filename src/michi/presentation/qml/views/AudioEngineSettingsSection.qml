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
//
// M11.3-UI-R1 corrective seal:
//  - P1-01: advanced disclosure `expanded` lives on the OUTER section
//    (advancedSection) — single unambiguous owner, no dynamic properties.
//  - P1-06: every surface has content-derived implicit sizing (cards,
//    fallback banner) — no collapsed geometry.
//  - P2-01: raw technical error is NOT in the normal fallback surface;
//    it appears only under Advanced engine details.
//  - P2-05: engine cards are disabled while a switch is in flight.
//  - Keyboard: cards and the advanced disclosure are real Buttons with
//    visible focus, Accessible names and Enter/Space activation.
Item {
    id: root

    property var engines: []
    property string selectedEngineId: ""
    property string activeEngineId: ""
    property string lifecycleLabel: ""
    property string fallbackFrom: ""
    property string errorMessage: ""
    property string statusSummary: ""
    property string switchingTo: ""

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
                        objectName: "audioEnginePreferredValue"
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
                        objectName: "audioEngineActiveValue"
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
            // P2-01: HUMAN COPY ONLY — raw technical error is never shown
            // here; it lives under Advanced engine details.
            Rectangle {
                id: fallbackBanner
                objectName: "audioEngineFallbackBanner"
                visible: root.fallbackFrom !== ""
                    && root.selectedEngineId !== root.activeEngineId
                Layout.fillWidth: true
                radius: MichiRadius.md
                color: MichiSemanticColors.contentSurface
                border.width: 1
                border.color: MichiSemanticColors.borderSubtle
                Layout.topMargin: MichiTheme.space4
                // P1-06: content-derived height (never collapsed).
                implicitHeight: fallbackContent.implicitHeight
                    + MichiTheme.space12 + MichiTheme.space12

                ColumnLayout {
                    id: fallbackContent
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
                }
            }

            // ── Engine cards (plain language, truthful, keyboard-able) ─
            Repeater {
                id: engineCards
                model: root.engines
                delegate: Button {
                    id: card
                    required property var modelData
                    required property int index
                    objectName: "engineSettingsCard_" + card.modelData.id
                    Layout.fillWidth: true
                    Layout.topMargin: MichiTheme.space4
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    // Application owns the semantic plan; Settings and the
                    // popup consume the exact same readiness/action roles.
                    enabled: card.modelData.selectionAllowed
                        && card.modelData.selectionAction !== "noop"
                        && !card.modelData.switching
                    padding: 0
                    leftPadding: MichiTheme.space12
                    rightPadding: MichiTheme.space12
                    topPadding: MichiTheme.space12
                    bottomPadding: MichiTheme.space12

                    property bool isActive: card.modelData.id === root.activeEngineId
                    property bool isSelected: card.modelData.id === root.selectedEngineId

                    function statusText() {
                        if (card.modelData.switching)
                            return qsTr("Switching…")
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

                    onClicked: root.engineSwitchRequested(card.modelData.id)
                    Keys.onReturnPressed: card.clicked()
                    Keys.onEnterPressed: card.clicked()
                    KeyNavigation.up: root._navigate(index, -1)
                    KeyNavigation.down: root._navigate(index, 1)

                    Accessible.name: card.modelData.displayName + " — " + card.statusText()
                    Accessible.description: card.modelData.selectionAllowed
                        ? qsTr("Select ") + card.modelData.displayName
                        : card.modelData.selectionBlocker

                    // P1-06: Button derives implicitHeight from the content
                    // column + padding — real positive geometry, wrapping
                    // descriptions, translation-safe.
                    contentItem: ColumnLayout {
                        id: cardContent
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
                                objectName: "engineSettingsCardStatus_" + card.modelData.id
                                text: card.statusText()
                                font.pixelSize: MichiTheme.fontSizeBody
                                font.weight: MichiTheme.fontWeightBold
                                color: card.isActive
                                    ? MichiPalette.auroraCyan
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
                    }

                    background: Rectangle {
                        radius: MichiRadius.md
                        color: card.pressed
                            ? MichiSemanticColors.surfacePressed
                            : card.hovered
                                ? MichiSemanticColors.surfaceHover
                                : card.isSelected
                                    ? MichiSemanticColors.contentSurface
                                    : "transparent"
                        border.width: card.visualFocus ? 1 : (card.isSelected ? 1 : 0)
                        border.color: card.visualFocus
                            ? MichiSemanticColors.focusRing
                            : card.isSelected
                                ? MichiSemanticColors.borderStrong
                                : "transparent"
                    }
                }
            }

            // ── Advanced engine details (progressive disclosure) ───────
            // P1-01: `expanded` belongs to THIS section (advancedSection);
            // the inner content only READS it. The disclosure header is a
            // real Button: mouse AND keyboard (Enter/Space) activation.
            ColumnLayout {
                id: advancedSection
                Layout.topMargin: MichiTheme.space8
                spacing: MichiTheme.space8
                property bool expanded: false

                Button {
                    objectName: "engineAdvancedToggle"
                    Layout.fillWidth: true
                    implicitHeight: 34
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    padding: 0
                    onClicked: advancedSection.expanded = !advancedSection.expanded
                    Keys.onReturnPressed: advancedSection.expanded = !advancedSection.expanded
                    Keys.onEnterPressed: advancedSection.expanded = !advancedSection.expanded
                    Accessible.name: advancedSection.expanded
                        ? qsTr("Hide advanced engine details")
                        : qsTr("Advanced engine details")

                    contentItem: Text {
                        text: advancedSection.expanded
                            ? qsTr("Hide advanced engine details")
                            : qsTr("Advanced engine details")
                        anchors.centerIn: parent
                        font.pixelSize: MichiTheme.fontSizeBody
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiPalette.textSecondary
                    }

                    background: Rectangle {
                        radius: MichiRadius.md
                        color: parent.hovered
                            ? MichiSemanticColors.surfaceHover : "transparent"
                        border.width: parent.visualFocus ? 1 : 0
                        border.color: MichiSemanticColors.focusRing
                    }
                }

                ColumnLayout {
                    id: advancedContent
                    objectName: "engineAdvancedContent"
                    visible: advancedSection.expanded
                    spacing: MichiTheme.space4
                    Layout.fillWidth: true

                    // P2-01: the ONLY surface where raw technical failure
                    // text appears (canonical service error_message).
                    Text {
                        visible: root.errorMessage !== ""
                        text: qsTr("Technical failure reason: %1")
                            .arg(root.errorMessage)
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiPalette.textSecondary
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

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

    // P2-02 (M11.3-UI-R2): Up/Down navigation SKIPS non-selectable cards
    // (unavailable / disabled / mid-switch lock). No wrapping.
    function _navigate(fromIndex, delta) {
        var count = engineCards.count
        var i = fromIndex + delta
        while (i >= 0 && i < count) {
            var item = engineCards.itemAt(i)
            if (item !== null && item.enabled)
                return item
            i += delta
        }
        return null
    }

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
