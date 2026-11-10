import QtQuick
import QtQuick.Layouts
import "../controls"
import "../theme"

// Shared rows + footer actions body for list-like Ecosystem cards.
ColumnLayout {
    id: root

    property var card: ({})
    signal actionTriggered(string action, string route)

    spacing: MichiSpacing.sm

    Repeater {
        model: root.card.items ?? []

        delegate: EcosystemStatusRow {
            required property var modelData
            Layout.fillWidth: true
            label: modelData.label ?? ""
            status: modelData.status ?? ""
            tone: modelData.tone ?? "neutral"
        }
    }

    Item { Layout.fillHeight: true }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        Item { Layout.fillWidth: true }

        MichiButton {
            visible: (root.card.secondaryAction ?? "").length > 0
            text: root.card.secondaryAction ?? ""
            variant: "ghost"
            onClicked: root.actionTriggered(
                "secondary", root.card.secondaryRoute ?? "")
        }

        MichiButton {
            visible: (root.card.primaryAction ?? "").length > 0
            text: root.card.primaryAction ?? ""
            variant: "primary"
            onClicked: root.actionTriggered(
                "primary", root.card.primaryRoute ?? root.card.route ?? "")
        }
    }
}
