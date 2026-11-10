import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// Physical organization only; playback remains in Michi Control.
EcosystemCardSurface {
    id: root

    property var card: ({})
    signal actionTriggered(string action, string route)

    title: card.title ?? ""
    subtitle: card.subtitle ?? ""
    icon: card.icon ?? ""
    eyebrow: card.eyebrow ?? ""
    status: card.status ?? ""
    statusTone: card.statusTone ?? "neutral"
    highlighted: card.highlighted ?? false
    interactive: true
    onActivated: root.actionTriggered("open", card.route ?? "")

    Flow {
        Layout.fillWidth: true
        spacing: MichiSpacing.sm

        Repeater {
            model: root.card.items ?? []
            delegate: MichiStatusChip {
                required property var modelData
                text: modelData.label ?? ""
                tone: modelData.tone ?? "neutral"
                dotVisible: false
            }
        }
    }

    Item { Layout.fillHeight: true }

    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        MichiButton {
            visible: (root.card.primaryAction ?? "").length > 0
            text: root.card.primaryAction ?? ""
            variant: "ghost"
            onClicked: root.actionTriggered(
                "primary", root.card.primaryRoute ?? root.card.route ?? "")
        }
    }
}
