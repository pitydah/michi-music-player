import QtQuick
import QtQuick.Layouts
import "../theme"

// Ecosystem dashboard layout engine.
//
// The Player design system owns responsive thresholds.  Ecosystem only maps
// those canonical bands to a stable asymmetric layout; it never invents its
// own breakpoints.
Item {
    id: root

    property var cards: []

    signal cardActivated(string route)
    signal cardActionTriggered(string action, string route)

    readonly property string breakpointClass: MichiBreakpoints.classFor(width)
    readonly property int columns: breakpointClass === "xl" ? 12
        : breakpointClass === "wide" ? 8
        : breakpointClass === "medium" ? 6
        : breakpointClass === "compact" ? 2 : 1

    implicitHeight: grid.implicitHeight

    function _spanFor(kind, columns) {
        if (columns >= 12) {
            switch (kind) {
            case "discovery": return { c: 0, r: 0, cs: 5, rs: 2 };
            case "music_stream": return { c: 5, r: 0, cs: 7, rs: 1 };
            case "spaces": return { c: 5, r: 1, cs: 7, rs: 1 };
            case "micro_server": return { c: 0, r: 2, cs: 4, rs: 1 };
            case "michi_link": return { c: 4, r: 2, cs: 4, rs: 1 };
            case "mobile": return { c: 8, r: 2, cs: 4, rs: 1 };
            case "devices": return { c: 0, r: 3, cs: 8, rs: 1 };
            case "health": return { c: 8, r: 3, cs: 4, rs: 1 };
            case "integrations": return { c: 0, r: 4, cs: 6, rs: 1 };
            case "account": return { c: 6, r: 4, cs: 3, rs: 1 };
            case "create_stream": return { c: 9, r: 4, cs: 3, rs: 1 };
            }
            return { c: -1, r: -1, cs: 6, rs: 1 };
        }
        if (columns === 8) {
            switch (kind) {
            case "discovery": return { c: -1, r: -1, cs: 8, rs: 1 };
            case "integrations": return { c: -1, r: -1, cs: 4, rs: 1 };
            case "account": return { c: -1, r: -1, cs: 4, rs: 1 };
            case "create_stream": return { c: -1, r: -1, cs: 4, rs: 1 };
            default: return { c: -1, r: -1, cs: 4, rs: 1 };
            }
        }
        if (columns === 6) {
            switch (kind) {
            case "discovery": return { c: -1, r: -1, cs: 6, rs: 1 };
            case "integrations": return { c: -1, r: -1, cs: 6, rs: 1 };
            default: return { c: -1, r: -1, cs: 3, rs: 1 };
            }
        }
        if (columns === 2)
            return { c: -1, r: -1, cs: kind === "discovery" ? 2 : 1, rs: 1 };
        return { c: -1, r: -1, cs: 1, rs: 1 };
    }

    function _componentFor(kind) {
        switch (kind) {
        case "discovery": return discoveryCard;
        case "music_stream": return musicStreamCard;
        case "spaces": return spacesCard;
        case "micro_server": return microServerCard;
        case "michi_link": return michiLinkCard;
        case "mobile": return mobileCard;
        case "devices": return devicesCard;
        case "health": return healthCard;
        case "integrations": return integrationsCard;
        case "account": return accountCard;
        case "create_stream": return addDeviceCard;
        }
        return null;
    }

    function _relayCard(route) {
        if (route && route.length > 0)
            root.cardActivated(route);
    }

    function _relayAction(action, route) {
        // Action buttons have their own navigation signal.  Do not also emit
        // cardActivated or the Player navigation host receives the route twice.
        root.cardActionTriggered(action, route ?? "");
    }

    GridLayout {
        id: grid
        objectName: "ecosystemDashboardGrid"
        anchors.fill: parent
        columns: root.columns
        columnSpacing: MichiSpacing.md
        rowSpacing: MichiSpacing.md

        Repeater {
            model: root.cards

            delegate: Loader {
                id: cell
                required property var modelData

                readonly property var span: root._spanFor(
                    modelData.kind ?? "", root.columns)

                Layout.column: span.c
                Layout.row: span.r
                Layout.columnSpan: span.cs
                Layout.rowSpan: span.rs
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: root.columns <= 2 ? 136 : 120

                sourceComponent: root._componentFor(modelData.kind ?? "")

                onLoaded: {
                    if (!item)
                        return;
                    item.card = modelData;
                    item.activated.connect(root._relayCard);
                    item.actionTriggered.connect(root._relayAction);
                }
            }
        }
    }

    Component { id: discoveryCard; DiscoveryCard {} }
    Component { id: musicStreamCard; MusicStreamCard {} }
    Component { id: spacesCard; SpacesCard {} }
    Component { id: microServerCard; MicroServerCard {} }
    Component { id: michiLinkCard; MichiLinkCard {} }
    Component { id: mobileCard; MobileCard {} }
    Component { id: devicesCard; DevicesCard {} }
    Component { id: healthCard; HealthCard {} }
    Component { id: integrationsCard; IntegrationsCard {} }
    Component { id: accountCard; AccountCard {} }
    Component { id: addDeviceCard; AddDeviceCard {} }
}
