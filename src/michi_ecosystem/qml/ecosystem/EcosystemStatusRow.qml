import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

// A compact label + status row used by Ecosystem cards.
RowLayout {
    id: root

    property string label: ""
    property string status: ""
    property string tone: "neutral"

    spacing: MichiSpacing.sm

    MichiText {
        Layout.fillWidth: true
        text: root.label
        role: "body"
        elide: Text.ElideRight
    }

    MichiStatusChip {
        visible: root.status.length > 0
        text: root.status
        tone: root.tone
        dotVisible: root.tone !== "neutral"
    }
}
