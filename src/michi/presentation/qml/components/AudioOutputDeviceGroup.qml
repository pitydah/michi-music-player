pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    property var group: ({})
    property var signalPath: []
    property var reasonCodes: []
    property bool expanded: !(root.group.collapsedByDefault || false)
    signal selectionRequested(string stableDeviceId)
    spacing: MichiSpacing.xs

    Button {
        id: header
        objectName: "audioOutputGroup_" + (root.group.groupId || "group")
        Layout.fillWidth: true
        visible: (root.group.label || "") !== ""
        implicitHeight: 38
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded
        Keys.onReturnPressed: header.clicked()
        Keys.onEnterPressed: header.clicked()
        Accessible.name: (root.expanded ? qsTr("Collapse ") : qsTr("Expand "))
            + (root.group.label || qsTr("audio outputs"))

        contentItem: RowLayout {
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: root.group.label || ""
                role: "primary"
                font.weight: Font.DemiBold
            }
            MichiText {
                text: qsTr("%1 output(s)").arg((root.group.rows || []).length)
                role: "secondary"
            }
            MichiText {
                text: root.expanded ? "▾" : "›"
                role: "secondary"
            }
        }
        background: Rectangle {
            radius: MichiRadius.sm
            color: header.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            border.width: header.visualFocus ? 1 : 0
            border.color: MichiSemanticColors.focusRing
        }
    }

    MichiText {
        visible: root.expanded && (root.group.description || "") !== ""
        Layout.fillWidth: true
        text: root.group.description || ""
        role: "secondary"
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: root.expanded ? (root.group.rows || []) : []
        delegate: DacDeviceCard {
            id: card
            required property var modelData
            Layout.fillWidth: true
            device: card.modelData
            signalPath: card.modelData.active ? root.signalPath : []
            reasonCodes: card.modelData.active ? root.reasonCodes : []
            onSelectionRequested: stableDeviceId => root.selectionRequested(stableDeviceId)
        }
    }
}
