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
        content.implicitHeight + (root.compact ? MichiSpacing.sm : MichiSpacing.md))
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
                color: MichiPalette.smoke
                border.width: 1
                border.color: MichiSemanticColors.borderSubtle
                MichiSignalStageIcon {
                    anchors.centerIn: parent
                    width: 20
                    height: 20
                    roleName: root.iconName
                    iconColor: MichiPalette.textPrimary
                }
            }
            // Evidence is NOT the identity icon. It is a separate badge.
            Rectangle {
                x: 26
                y: 34
                width: 15
                height: 15
                radius: 7.5
                color: MichiPalette.smoke
                border.width: 1
                border.color: root.stateColor
                MichiIcon {
                    anchors.centerIn: parent
                    name: root.glyphName
                    width: 9
                    height: 9
                    iconColor: root.stateColor
                }
            }
        }

        ColumnLayout {
            id: content
            Layout.fillWidth: true
            Layout.topMargin: root.compact ? MichiSpacing.xs : MichiSpacing.sm
            spacing: root.compact ? 1 : MichiSpacing.xxs

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.sm

                MichiText {
                    text: root.title
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
                Item { Layout.fillWidth: true }
                MichiText {
                    text: root.stateText
                    role: "micro"
                    color: root.stateColor
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
                visible: root.expanded && root.detail !== ""
                text: root.detail
                role: "caption"
                color: MichiPalette.textMuted
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
                            role: "micro"
                            color: MichiPalette.textMuted
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
