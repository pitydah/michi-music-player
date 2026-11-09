import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// One truthful stage of the Signal Truth path. The rail is driven by explicit
// index/count flags, never by the item's y position. Detail disclosure comes
// before any configuration affordance.
Item {
    id: root
    property int stageIndex: 0
    property int stageCount: 1
    property bool compact: false
    property bool first: stageIndex === 0
    property bool last: stageIndex === Math.max(0, stageCount - 1)
    property bool expanded: false
    property bool expandable: false
    property string iconName: "track"
    property string title: ""
    property string summary: ""
    property string detail: ""
    property string configAction: "NONE"
    property string stageState: "unknown"
    property var detailRows: []

    signal toggleRequested()
    signal configurationRequested(string action)

    readonly property color stateColor: root.stageState === "observed"
        ? MichiPalette.success
        : root.stageState === "transformed" ? MichiPalette.auroraCyan
        : root.stageState === "pending" ? MichiPalette.auroraBlue
        : root.stageState === "historical" ? MichiPalette.textSecondary
        : root.stageState === "error" ? MichiPalette.error
        : MichiPalette.textMuted
    readonly property string stateText: root.stageState === "observed"
        ? qsTr("Observed")
        : root.stageState === "transformed" ? qsTr("Transformed")
        : root.stageState === "pending" ? qsTr("Pending")
        : root.stageState === "historical" ? qsTr("Historical")
        : root.stageState === "error" ? qsTr("Error")
        : qsTr("Unknown")
    readonly property string glyphName: root.stageState === "observed"
        ? "check"
        : root.stageState === "transformed" ? "equalizer"
        : root.stageState === "historical" ? "history"
        : root.stageState === "error" ? "info"
        : root.stageState === "pending" ? "history"
        : "info"
    readonly property color segmentColor: root.stageState === "transformed"
        ? MichiPalette.auroraCyan
        : root.stageState === "error" ? MichiPalette.error
        : root.stageState === "pending" ? MichiPalette.auroraBlue
        : MichiPalette.textMuted

    // The height is content-driven, including expanded evidence rows.
    implicitHeight: Math.max(root.compact ? 64 : 76,
        content.implicitHeight)
    activeFocusOnTab: root.expandable
    Accessible.role: root.expandable ? Accessible.Button : Accessible.StaticText
    Accessible.name: qsTr("%1: %2. %3").arg(root.title).arg(root.summary).arg(
        root.stateText)
    Accessible.description: root.detail
    Keys.onReturnPressed: event => {
        if (root.expandable) { root.toggleRequested(); event.accepted = true }
    }
    Keys.onSpacePressed: event => {
        if (root.expandable) { root.toggleRequested(); event.accepted = true }
    }
    Keys.onDownPressed: event => {
        if (!root.expandable) return
        const next = root.nextItemInFocusChain(true)
        if (next) { next.forceActiveFocus(); event.accepted = true }
    }
    Keys.onUpPressed: event => {
        if (!root.expandable) return
        const previous = root.nextItemInFocusChain(false)
        if (previous) { previous.forceActiveFocus(); event.accepted = true }
    }

    // Keyboard focus must be visible without relying on color alone: the
    // border encloses the whole stage and remains readable in both densities.
    Rectangle {
        objectName: "stageFocusRing"
        anchors.fill: parent
        color: "transparent"
        radius: 12
        border.width: root.activeFocus && root.expandable ? 2 : 0
        border.color: MichiPalette.auroraCyan
    }

    // EXCLUSIVE mouse owner. Unlike a passive TapHandler, this accepts the
    // event; no TrackRow beneath this popup may receive the same pointer tap.
    // Nested explicit buttons render above this background input surface.
    MouseArea {
        anchors.fill: parent
        enabled: root.expandable
        acceptedButtons: Qt.LeftButton
        preventStealing: true
        propagateComposedEvents: false
        onClicked: root.toggleRequested()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.preferredWidth: root.compact ? 42 : 46
            Layout.fillHeight: true

            // Continuous rail follows the WHOLE delegate height; expansion
            // cannot leave a fixed 40px disconnected segment.
            Rectangle {
                visible: !root.first
                x: 17
                y: 0
                width: 2
                height: 10
                color: root.segmentColor
                opacity: 0.75
            }
            Rectangle {
                visible: !root.last
                x: 17
                y: 42
                width: 2
                height: Math.max(0, parent.height - 42)
                color: root.segmentColor
                opacity: 0.75
            }
            Rectangle {
                x: 2
                y: 10
                width: 32
                height: 32
                radius: 10
                color: root.expanded ? MichiSemanticColors.controlSurfaceStrong
                    : MichiPalette.smoke
                border.width: 1
                border.color: root.expanded
                    ? MichiSemanticColors.auroraCyanBorder : MichiSemanticColors.borderSubtle
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiSignalStageIcon {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    roleName: root.iconName
                    iconColor: MichiPalette.textPrimary
                }
            }
            // Evidence is a discrete microdot, NOT a repeated checkmark icon.
            Rectangle {
                x: 26
                y: 33
                width: 14
                height: 14
                radius: width / 2
                color: MichiPalette.obsidianRaised
                border.width: 1
                border.color: root.stateColor
                Rectangle {
                    anchors.centerIn: parent
                    width: 6
                    height: 6
                    radius: width / 2
                    color: root.stateColor
                }
            }
        }

        ColumnLayout {
            id: content
            Layout.fillWidth: true
            Layout.topMargin: root.compact ? 0 : MichiSpacing.sm
            spacing: root.compact ? 1 : MichiSpacing.xxs

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.sm

                MichiText {
                    text: (root.stageIndex + 1 < 10 ? "0" : "")
                        + (root.stageIndex + 1) + "  "
                        + root.title.toUpperCase()
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
                Item { Layout.fillWidth: true }
                MichiText {
                    // The global route status already communicates ordinary
                    // observations; reserve per-stage text for useful exceptions.
                    visible: root.stageState !== "observed"
                        && root.stageState !== "historical"
                    text: root.stateText
                    role: "micro"
                    color: root.stateColor
                }
                MichiIconButton {
                    // Roon-like per-stage settings, explicitly invoked by user.
                    visible: root.configAction !== "NONE"
                    iconName: "settings"
                    accessibleName: qsTr("Configure %1").arg(root.title)
                    implicitWidth: MichiMetrics.controlSmall
                    implicitHeight: MichiMetrics.controlSmall
                    onClicked: root.configurationRequested(root.configAction)
                }
                MichiIconButton {
                    visible: root.expandable
                    iconName: root.expanded ? "chevron-down" : "chevron-right"
                    accessibleName: root.expanded
                        ? qsTr("Hide details for %1").arg(root.title)
                        : qsTr("Show details for %1").arg(root.title)
                    implicitWidth: MichiMetrics.controlSmall
                    implicitHeight: MichiMetrics.controlSmall
                    onClicked: root.toggleRequested()
                }
            }

            MichiText {
                text: root.summary
                role: "body"
                Layout.fillWidth: true
                wrapMode: root.expanded ? Text.WrapAnywhere : Text.NoWrap
                elide: root.expanded ? Text.ElideNone : Text.ElideRight
            }

            MichiText {
                objectName: "stageDetailText"
                visible: root.expanded && root.detail !== ""
                text: root.detail
                role: "secondary"
                color: MichiPalette.textSecondary
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            ColumnLayout {
                visible: root.expanded && root.detailRows.length > 0
                Layout.fillWidth: true
                spacing: 0

                Repeater {
                    model: root.detailRows
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: MichiSpacing.md
                        MichiText {
                            Layout.preferredWidth: 96
                            text: modelData[0]
                            role: "caption"
                            color: MichiPalette.textSecondary
                        }
                        MichiText {
                            Layout.fillWidth: true
                            text: modelData[1]
                            role: "technical"
                            technical: true
                            color: MichiPalette.textSecondary
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }

            MichiButton {
                visible: root.expanded && root.configAction !== "NONE"
                text: root.configAction === "OPEN_ENGINE" ? qsTr("Open Audio Engine")
                    : root.configAction === "OPEN_PROCESSING" ? qsTr("Open Equalizer")
                    : root.configAction === "OPEN_OUTPUT" ? qsTr("Open Output")
                    : qsTr("Open Device Setup")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlSmall
                onClicked: root.configurationRequested(root.configAction)
            }
        }
    }
}
