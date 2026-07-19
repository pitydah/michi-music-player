import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../materials"
import "../components"
import "../components/foundations"

Item {
    id: root
    objectName: "sidebar"
    focus: true
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Sidebar")

    property string currentRoute: "home"
    property bool deliveryMode: typeof appStateBridge !== "undefined" && appStateBridge
                                ? appStateBridge.deliveryMode : false
    property bool _userCollapsed: false
    property bool forceCompact: false
    property bool collapsed: forceCompact || _userCollapsed
    property var expandedGroups: ({})
    property var registry: typeof routeRegistryBridge !== "undefined"
                           ? routeRegistryBridge : null
    readonly property string canonicalCurrentRoute: registry
                                                    ? registry.resolveRoute(currentRoute)
                                                    : currentRoute

    signal routeRequested(string route)

    implicitWidth: collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth

    function iconPath(iconKey) {
        return iconKey ? "../../icons/sidebar/" + iconKey + ".svg" : ""
    }

    function isGroupExpanded(groupRoute) {
        return expandedGroups[groupRoute] === true
    }

    function persistExpandedGroups() {
        if (typeof pageStateStore !== "undefined" && pageStateStore)
            pageStateStore.saveState("__sidebar__", {"expandedGroups": expandedGroups})
    }

    function restoreExpandedGroups() {
        if (typeof pageStateStore === "undefined" || !pageStateStore
                || !pageStateStore.hasState("__sidebar__"))
            return
        var saved = pageStateStore.restoreState("__sidebar__")
        if (saved && saved.expandedGroups)
            expandedGroups = saved.expandedGroups
    }

    function toggleGroup(groupRoute) {
        var updated = {}
        for (var key in expandedGroups) {
            if (expandedGroups.hasOwnProperty(key))
                updated[key] = expandedGroups[key]
        }
        updated[groupRoute] = !updated[groupRoute]
        expandedGroups = updated
        persistExpandedGroups()
    }

    function autoExpandForRoute(route) {
        if (!registry)
            return
        var canonical = registry.resolveRoute(route)
        var parent = registry.getParentRoute(canonical)
        if (!parent || expandedGroups[parent] === true)
            return
        var updated = {}
        for (var key in expandedGroups) {
            if (expandedGroups.hasOwnProperty(key))
                updated[key] = expandedGroups[key]
        }
        updated[parent] = true
        expandedGroups = updated
        persistExpandedGroups()
    }

    function isParentActive(parentRoute) {
        return registry
                ? registry.isChildActive(parentRoute, canonicalCurrentRoute)
                : canonicalCurrentRoute === parentRoute
    }

    onCurrentRouteChanged: autoExpandForRoute(currentRoute)

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) { root.autoExpandForRoute(route) }
    }

    Component {
        id: mainSectionDelegate

        Item {
            id: section
            width: root.width
            property var spec: modelData
            property string sectionRoute: spec.route || ""
            property string sectionTitle: spec.title || ""
            property string sectionIcon: spec.icon || ""
            property bool expandable: spec.expandable || false
            property var children: spec.children || []
            property bool expanded: root.isGroupExpanded(sectionRoute)
            height: mainRow.height + ((!root.collapsed && expanded) ? childColumn.height : 0)

            Rectangle {
                id: mainRow
                objectName: "sidebarMain_" + section.sectionRoute
                width: parent.width
                height: root.collapsed ? 48 : 44
                radius: MichiTheme.radius.sm
                color: root.isParentActive(section.sectionRoute) && !root.collapsed
                       ? MichiTheme.colors.accentSelection : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.collapsed ? 10 : MichiTheme.spacing.md
                    anchors.rightMargin: root.collapsed ? 10 : MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Image {
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        Layout.alignment: Qt.AlignVCenter
                        source: root.iconPath(section.sectionIcon)
                        sourceSize.width: 20
                        sourceSize.height: 20
                        fillMode: Image.PreserveAspectFit
                        opacity: root.isParentActive(section.sectionRoute) ? 1.0 : 0.82
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: !root.collapsed
                        text: section.sectionTitle
                        color: root.isParentActive(section.sectionRoute)
                               ? MichiTheme.colors.textPrimary
                               : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: root.isParentActive(section.sectionRoute)
                                     ? MichiTheme.typography.weightMedium
                                     : MichiTheme.typography.weightNormal
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.preferredWidth: 20
                        visible: section.expandable && !root.collapsed && section.children.length > 0
                        text: section.expanded ? "▾" : "▸"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: 10
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                MouseArea {
                    id: mainAction
                    objectName: "sidebarMainAction_" + section.sectionRoute
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: parent.width - (chevronAction.visible ? chevronAction.width : 0)
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    Accessible.role: Accessible.Button
                    Accessible.name: section.sectionTitle
                    onClicked: root.routeRequested(section.sectionRoute)
                }

                MouseArea {
                    id: chevronAction
                    objectName: "sidebarChevron_" + section.sectionRoute
                    visible: section.expandable && !root.collapsed && section.children.length > 0
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 40
                    cursorShape: Qt.PointingHandCursor
                    activeFocusOnTab: visible
                    Accessible.role: Accessible.Button
                    Accessible.name: section.expanded
                                     ? qsTr("Contraer %1").arg(section.sectionTitle)
                                     : qsTr("Expandir %1").arg(section.sectionTitle)
                    Keys.onReturnPressed: root.toggleGroup(section.sectionRoute)
                    Keys.onSpacePressed: root.toggleGroup(section.sectionRoute)
                    onClicked: root.toggleGroup(section.sectionRoute)
                }

                ToolTip {
                    visible: root.collapsed && mainAction.containsMouse
                    text: section.sectionTitle
                    delay: 600
                }
            }

            Column {
                id: childColumn
                anchors.top: mainRow.bottom
                width: parent.width
                visible: section.expandable && section.children.length > 0
                         && section.expanded && !root.collapsed

                Repeater {
                    model: section.children

                    delegate: Item {
                        id: child
                        width: root.width
                        height: 38
                        property var childSpec: modelData
                        property string childRoute: childSpec.route || ""
                        property string childTitle: childSpec.title || ""
                        property string childIcon: childSpec.icon || ""
                        property string childStatus: childSpec.status || "functional"

                        Rectangle {
                            id: childRow
                            objectName: "sidebarChild_" + child.childRoute
                            width: parent.width - 16
                            height: parent.height - 2
                            anchors.centerIn: parent
                            radius: MichiTheme.radius.sm
                            color: root.canonicalCurrentRoute === child.childRoute
                                   ? MichiTheme.colors.accentSelection : "transparent"

                            Rectangle {
                                visible: root.canonicalCurrentRoute === child.childRoute
                                width: 2
                                height: 16
                                anchors.left: parent.left
                                anchors.leftMargin: 4
                                anchors.verticalCenter: parent.verticalCenter
                                radius: 1
                                color: MichiTheme.colors.accentBlue
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: MichiTheme.spacing.xl
                                anchors.rightMargin: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.sm

                                Image {
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    source: root.iconPath(child.childIcon)
                                    sourceSize.width: 16
                                    sourceSize.height: 16
                                    fillMode: Image.PreserveAspectFit
                                    opacity: root.canonicalCurrentRoute === child.childRoute ? 1.0 : 0.78
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: child.childTitle
                                    color: root.canonicalCurrentRoute === child.childRoute
                                           ? MichiTheme.colors.textPrimary
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.bodySize - 1
                                    font.weight: root.canonicalCurrentRoute === child.childRoute
                                                 ? MichiTheme.typography.weightMedium
                                                 : MichiTheme.typography.weightNormal
                                    elide: Text.ElideRight
                                }

                                StatusBadge {
                                    visible: child.childStatus !== "functional"
                                    text: child.childStatus === "planned" ? qsTr("Planificado")
                                          : child.childStatus === "experimental" ? qsTr("Experimental")
                                          : child.childStatus === "partial" ? qsTr("Parcial")
                                          : child.childStatus === "configuration_required" ? qsTr("Configurar")
                                          : ""
                                    kind: child.childStatus === "experimental" ? "experimental"
                                          : child.childStatus === "configuration_required" ? "warning"
                                          : "info"
                                }
                            }

                            MouseArea {
                                id: childAction
                                objectName: "sidebarChildAction_" + child.childRoute
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                activeFocusOnTab: true
                                Accessible.role: Accessible.Button
                                Accessible.name: qsTr("%1, subsección de %2")
                                                 .arg(child.childTitle).arg(section.sectionTitle)
                                Keys.onReturnPressed: root.routeRequested(child.childRoute)
                                Keys.onSpacePressed: root.routeRequested(child.childRoute)
                                onClicked: root.routeRequested(child.childRoute)
                            }
                        }
                    }
                }
            }
        }
    }

    SidebarMaterial {
        anchors.fill: parent

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: mainColumn.height + MichiTheme.spacing.xxl
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: mainColumn
                    width: root.width
                    spacing: 0

                    Item { width: 1; height: MichiTheme.spacing.md }

                    Repeater {
                        model: root.registry ? root.registry.sidebarSections : []
                        delegate: mainSectionDelegate
                    }

                    Item { width: 1; height: MichiTheme.spacing.md }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: MichiTheme.borderWidth
                color: MichiTheme.colors.borderSubtle
            }

            Column {
                id: fixedColumn
                Layout.fillWidth: true
                spacing: 0

                Repeater {
                    model: root.registry ? root.registry.sidebarFixedItems : []

                    delegate: Item {
                        id: fixedItem
                        width: root.width
                        height: root.collapsed ? 48 : 44
                        property var spec: modelData

                        Rectangle {
                            objectName: "sidebarFixed_" + fixedItem.spec.route
                            anchors.fill: parent
                            radius: MichiTheme.radius.sm
                            color: root.canonicalCurrentRoute === fixedItem.spec.route
                                   ? MichiTheme.colors.accentSelection : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: root.collapsed ? 24 : MichiTheme.spacing.md
                                anchors.rightMargin: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                Image {
                                    Layout.preferredWidth: 20
                                    Layout.preferredHeight: 20
                                    source: root.iconPath(fixedItem.spec.icon || "")
                                    sourceSize.width: 20
                                    sourceSize.height: 20
                                }

                                Text {
                                    Layout.fillWidth: true
                                    visible: !root.collapsed
                                    text: fixedItem.spec.title || ""
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                activeFocusOnTab: true
                                Accessible.role: Accessible.Button
                                Accessible.name: fixedItem.spec.title || ""
                                Keys.onReturnPressed: root.routeRequested(fixedItem.spec.route)
                                Keys.onSpacePressed: root.routeRequested(fixedItem.spec.route)
                                onClicked: root.routeRequested(fixedItem.spec.route)
                            }
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        restoreExpandedGroups()
        autoExpandForRoute(currentRoute)
    }
}
