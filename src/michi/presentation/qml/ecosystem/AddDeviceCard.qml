import QtQuick
import QtQuick.Layouts
import "../controls"
import "../theme"

// One canonical entry into Stream Factory — never a second flash flow.
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
    onActivated: root.actionTriggered(
        "primary", card.primaryRoute ?? card.route ?? "")

    Item { Layout.fillHeight: true }

    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        MichiButton {
            text: root.card.primaryAction ?? ""
            variant: "primary"
            onClicked: root.actionTriggered(
                "primary", root.card.primaryRoute ?? root.card.route ?? "")
        }
    }
}
