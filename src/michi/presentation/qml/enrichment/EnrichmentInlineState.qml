import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../theme"

RowLayout {
    id: root

    property string kind: "artist"
    property string state: "IDLE"
    property string message: ""
    property bool busy: false
    property bool onlineEnabled: false
    property bool hasKnowledge: false
    property bool active: false

    signal refreshRequested()
    signal reviewRequested()
    signal clearRequested()
    signal resetRequested()

    readonly property bool shouldShowStatus: state !== "IDLE" && state !== "READY"
    readonly property bool shouldShowPrimary: onlineEnabled && !busy
        && (state === "AMBIGUOUS" || state === "NOT_FOUND"
            || state === "FAILED" || state === "OFFLINE" || state === "PARTIAL"
            || (state === "READY" && !hasKnowledge))

    Layout.fillWidth: true
    spacing: MichiSpacing.sm
    visible: active && (shouldShowStatus || shouldShowPrimary || hasKnowledge)

    EnrichmentStatusBar {
        Layout.fillWidth: true
        state: root.state
        message: root.message
        busy: root.busy
    }

    Item { Layout.fillWidth: !root.shouldShowStatus }

    MichiButton {
        text: root.state === "AMBIGUOUS" ? qsTr("Review match")
            : root.state === "READY" && !root.hasKnowledge
                ? qsTr("Fetch information") : qsTr("Retry")
        variant: "ghost"
        visible: root.shouldShowPrimary
        onClicked: {
            if (root.state === "AMBIGUOUS" || root.state === "NOT_FOUND")
                root.reviewRequested()
            else
                root.refreshRequested()
        }
    }

    MichiIconButton {
        id: moreButton
        iconName: "more"
        accessibleName: qsTr("Online information options")
        visible: root.hasKnowledge || root.state !== "IDLE"
        onClicked: optionsMenu.popup()

        MichiMenu {
            id: optionsMenu
            x: Math.max(0, parent.width - width)
            y: parent.height + MichiSpacing.xs
            MichiMenuItem {
                text: root.hasKnowledge ? qsTr("Refresh information")
                    : qsTr("Fetch information")
                icon.name: "refresh"
                visible: root.onlineEnabled && !root.busy
                onTriggered: root.refreshRequested()
            }
            MichiMenuItem {
                text: qsTr("Clear online information")
                icon.name: "close"
                visible: root.hasKnowledge
                onTriggered: root.clearRequested()
            }
            MichiSeparator { visible: root.hasKnowledge }
            MichiMenuItem {
                text: qsTr("Reset match")
                icon.name: "refresh"
                onTriggered: root.resetRequested()
            }
        }
    }
}
