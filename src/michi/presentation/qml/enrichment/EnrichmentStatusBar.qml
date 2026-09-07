import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

/* M6.9 — EnrichmentStatusBar: sober status line for the online knowledge
 * surface. CANCELLED is never rendered as an error; DISABLED is a policy
 * state, not a failure. The music stays the protagonist. */
RowLayout {
    id: root

    property string state: "IDLE"
    property string message: ""
    property bool busy: false

    spacing: MichiSpacing.md
    onStateChanged: root.visible = root.state !== "IDLE" && root.state !== "READY"
    onMessageChanged: root.visible = root.state !== "IDLE" && root.state !== "READY"

    function _tone() {
        switch (root.state) {
        case "FAILED": return "error"
        case "PARTIAL":
        case "OFFLINE":
        case "AMBIGUOUS": return "warning"
        case "RESOLVING_IDENTITY":
        case "FETCHING_KNOWLEDGE":
        case "NOT_FOUND": return "active"
        default: return "neutral"
        }
    }

    function _label() {
        switch (root.state) {
        case "DISABLED": return qsTr("Disabled")
        case "RESOLVING_IDENTITY": return qsTr("Finding")
        case "FETCHING_KNOWLEDGE": return qsTr("Loading")
        case "PARTIAL": return qsTr("Partial")
        case "OFFLINE": return qsTr("Offline")
        case "FAILED": return qsTr("Failed")
        case "AMBIGUOUS": return qsTr("Review needed")
        case "NOT_FOUND": return qsTr("No match")
        case "CANCELLED": return qsTr("Cancelled")
        default: return root.state
        }
    }

    MichiStatusChip {
        text: root._label()
        tone: root._tone()
        dotVisible: root.busy
    }

    MichiText {
        Layout.fillWidth: true
        text: root.message
        role: "secondary"
        elide: Text.ElideRight
        visible: root.message.length > 0
    }

    /* busy indicator — motion-safe */
    Item {
        Layout.preferredWidth: 14
        Layout.preferredHeight: 14
        visible: root.busy
        Rectangle {
            anchors.centerIn: parent
            width: 8
            height: 8
            radius: 4
            color: MichiPalette.auroraCyan
            opacity: root.busy ? 1.0 : 0.0
        }
    }
}
