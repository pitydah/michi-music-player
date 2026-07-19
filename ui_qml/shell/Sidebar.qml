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
    property string compactFlyoutRoute: ""
    property real compactFlyoutY: 0
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
            pageStateStore.saveState("__sidebar__", {
                "expandedGroups": expandedGroups,
                "userCollapsed": _userCollapsed
            })
    }

    function restoreExpandedGroups() {
        if (typeof pageStateStore === "undefined" || !pageStateStore
                || !pageStateStore.hasState("__sidebar__"))
            return
        var saved = pageStateStore.restoreState("__sidebar__")
        if (saved && saved.expandedGroups)
            expandedGroups = saved.expandedGroups
        if (saved && saved.userCollapsed !== undefined)
            _userCollapsed = saved.userCollapsed
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
        if (!parent)
            return
        if (expandedGroups[parent] !== true) {
            var updated = {}
            for (var key in expandedGroups) {
                if (expandedGroups.hasOwnProperty(key))
                    updated[key] = expandedGroups[key]
            }
            updated[parent] = true
            expandedGroups = updated
            persistExpandedGroups()
        }
        Qt.callLater(function() { ensureRouteVisible(canonical) })
    }

    function ensureRouteVisible(route) {
        if (!registry || !navigationFlickable)
            return
        var sections = registry.sidebarSections
        var y = MichiTheme.spacing.md
        for (var sectionIndex = 0; sectionIndex < sections.length; ++sectionIndex) {
            var section = sections[sectionIndex]
            if (section.route === route) {
                break
            }
            if (section.children) {
                for (var childIndex = 0; childIndex < section.children.length; ++childIndex) {
                    if (section.children[childIndex].route === route) {
                        y += 44 + childIndex * 44
                        sectionIndex = sections.length
                        break
                    }
                }
            }
            if (sectionIndex < sections.length)
                y += 44 + (isGroupExpanded(section.route) ? (section.children || []).length * 44 : 0)
        }
        if (y < navigationFlickable.contentY)
            navigationFlickable.contentY = Math.max(0, y - MichiTheme.spacing.sm)
        else if (y + 44 > navigationFlickable.contentY + navigationFlickable.height)
            navigationFlickable.contentY = Math.min(
                navigationFlickable.contentHeight - navigationFlickable.height,
                y + 44 - navigationFlickable.height)
    }

    function isParentActive(parentRoute) {
        return registry
                ? registry.isChildActive(parentRoute, canonicalCurrentRoute)
                : canonicalCurrentRoute === parentRoute
    }

    function toggleCollapsed() {
        _userCollapsed = !_userCollapsed
        compactFlyoutRoute = ""
        persistExpandedGroups()
    }

    function flyoutItems(groupRoute) {
        if (!registry)
            return []
        var sections = registry.sidebarSections
        for (var index = 0; index < sections.length; ++index) {
            var section = sections[index]
            if (section.route === groupRoute) {
                var items = [{"route": section.route, "title": section.title,
                              "icon": section.icon, "status": section.status}]
                return items.concat(section.children || [])
            }
        }
        return []
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

                Rectangle {
                    visible: root.isParentActive(section.sectionRoute)
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: 22
                    radius: MichiTheme.radius.xs
                    color: MichiTheme.colors.accentPrimary
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.collapsed ? 10 : MichiTheme.spacing.md
                    anchors.rightMargin: root.collapsed ? 10 : MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    MichiIcon {
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        Layout.alignment: Qt.AlignVCenter
                        iconKey: section.sectionIcon
                        size: 20
                        active: root.isParentActive(section.sectionRoute)
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

                    MichiIcon {
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                        visible: section.expandable && !root.collapsed && section.children.length > 0
                        source: "../../icons/nav_forward.svg"
                        size: 14
                        color: MichiTheme.colors.textMuted
                        rotation: section.expanded ? 90 : 0
                        Behavior on rotation {
                            NumberAnimation { duration: MichiTheme.motion.fast; easing.type: Easing.OutCubic }
                        }
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
                    activeFocusOnTab: true
                    function activate() {
                        if (root.collapsed && section.expandable && section.children.length > 0) {
                            root.compactFlyoutRoute = section.sectionRoute
                            root.compactFlyoutY = mainRow.mapToItem(root, 0, 0).y
                            compactFlyout.open()
                        } else {
                            root.routeRequested(section.sectionRoute)
                        }
                    }
                    Keys.onReturnPressed: activate()
                    Keys.onSpacePressed: activate()
                    onClicked: activate()
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
                        height: 44
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
                                color: MichiTheme.colors.accentPrimary
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: MichiTheme.spacing.xl
                                anchors.rightMargin: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.sm

                                MichiIcon {
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                    iconKey: child.childIcon
                                    size: 16
                                    active: root.canonicalCurrentRoute === child.childRoute
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

                                Rectangle {
                                    visible: child.childStatus !== "functional"
                                    Layout.preferredWidth: 7
                                    Layout.preferredHeight: 7
                                    radius: width / 2
                                    color: child.childStatus === "experimental"
                                           ? MichiTheme.colors.accentExperimental
                                           : child.childStatus === "configuration_required"
                                             ? MichiTheme.colors.warning
                                             : MichiTheme.colors.accentInfo

                                    ToolTip.visible: statusHover.containsMouse
                                    ToolTip.text: child.childStatus === "planned" ? qsTr("Planificado")
                                                  : child.childStatus === "experimental" ? qsTr("Experimental")
                                                  : child.childStatus === "partial" ? qsTr("Parcial")
                                                  : qsTr("Configuración requerida")
                                    MouseArea { id: statusHover; anchors.fill: parent; hoverEnabled: true }
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

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 64

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.collapsed ? 21 : MichiTheme.spacing.lg
                    anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    MichiIcon {
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 28
                        source: "../../icons/app_icon.svg"
                        size: 28
                        color: MichiTheme.colors.accentPrimary
                        accessibleName: qsTr("Michi Music Player")
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: !root.collapsed
                        text: "Michi Music Player"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    MichiIconButton {
                        visible: !root.forceCompact
                        iconSource: "../../icons/nav_back.svg"
                        rotation: root.collapsed ? 180 : 0
                        tooltipText: root.collapsed ? qsTr("Expandir sidebar") : qsTr("Contraer sidebar")
                        accessibleName: tooltipText
                        onClicked: root.toggleCollapsed()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: MichiTheme.borderWidth
                color: MichiTheme.colors.borderSubtle
            }

            Flickable {
                id: navigationFlickable
                objectName: "sidebarNavigationFlickable"
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

                                MichiIcon {
                                    Layout.preferredWidth: 20
                                    Layout.preferredHeight: 20
                                    iconKey: fixedItem.spec.icon || ""
                                    size: 20
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

    Popup {
        id: compactFlyout
        parent: Overlay.overlay
        x: root.width - 2
        y: Math.max(MichiTheme.spacing.sm,
                    Math.min(root.compactFlyoutY, root.height - height - MichiTheme.spacing.sm))
        width: 260
        height: Math.min(360, flyoutColumn.implicitHeight + MichiTheme.spacing.md * 2)
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: MichiTheme.spacing.md

        background: Rectangle {
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfacePopup
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
        }

        contentItem: Column {
            id: flyoutColumn
            spacing: MichiTheme.spacing.xs

            Repeater {
                model: root.flyoutItems(root.compactFlyoutRoute)

                delegate: Item {
                    id: flyoutItem
                    width: flyoutColumn.width
                    height: MichiTheme.minimumInteractiveSize
                    property var spec: modelData

                    RowLayout {
                        anchors.fill: parent
                        spacing: MichiTheme.spacing.sm
                        MichiIcon { iconKey: flyoutItem.spec.icon || ""; size: 18 }
                        Text {
                            Layout.fillWidth: true
                            text: flyoutItem.spec.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        activeFocusOnTab: true
                        cursorShape: Qt.PointingHandCursor
                        Accessible.role: Accessible.Button
                        Accessible.name: flyoutItem.spec.title || ""
                        function activate() {
                            root.routeRequested(flyoutItem.spec.route)
                            compactFlyout.close()
                        }
                        Keys.onReturnPressed: activate()
                        Keys.onSpacePressed: activate()
                        onClicked: activate()
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
