import QtQuick
import QtQuick.Layouts

// Canonical device inventory summary from Device Registry.
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

    EcosystemCardContent {
        Layout.fillWidth: true
        Layout.fillHeight: true
        card: root.card
        onActionTriggered: (action, route) => root.actionTriggered(action, route)
    }
}
