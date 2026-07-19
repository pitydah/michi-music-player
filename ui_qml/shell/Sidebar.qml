import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../materials"
import "../components"
import "../components/foundations"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar"
    objectName: "sidebar"
    focus: true
    id: root

    property string currentRoute: "home"
    property bool deliveryMode: typeof appStateBridge !== "undefined" && appStateBridge ? appStateBridge.deliveryMode : false
    signal routeRequested(string route)

    property bool _userCollapsed: false
    property bool forceCompact: false
    property bool collapsed: forceCompact || _userCollapsed
    property var expandedGroups: ({})
    property var registry: typeof routeRegistryBridge !== "undefined" ? routeRegistryBridge : null

    implicitWidth: collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth

    function isGroupExpanded(groupRoute) {
        return expandedGroups[groupRoute] === true
    }

    function toggleGroup(groupRoute) {
        var obj = {}
        for (var k in expandedGroups) {
            if (expandedGroups.hasOwnProperty(k)) obj[k] = expandedGroups[k]
        }
        obj[groupRoute] = !obj[groupRoute]
        expandedGroups = obj
    }

    function autoExpandForRoute(currentRoute) {
        if (!registry) return
        var parent = registry.getParentRoute(currentRoute)
        if (parent) {
            var obj = {}
            for (var k in expandedGroups) {
                if (expandedGroups.hasOwnProperty(k)) obj[k] = expandedGroups[k]
            }
            obj[parent] = true
            expandedGroups = obj
        }
    }

    function isParentActive(parentRoute) {
        if (!registry) return currentRoute === parentRoute
        return registry.isChildActive(parentRoute, currentRoute)
    }

    function getIconPath(iconKey) {
        if (!iconKey) return ""
        return "../../icons/sidebar/" + iconKey + ".svg"
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) { root.autoExpandForRoute(route) }
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
                contentHeight: contentColumn.height + MichiTheme.spacing.xxl
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    width: root.width
                    spacing: 0

                    Item { width: 1; height: MichiTheme.spacing.md }

                    Repeater {
                        model: root.registry ? root.registry.getSidebarSections() : []
                        delegate: Loader {
                            id: sectionLoader
                            width: root.width
                            property var sectionData: modelData
                            property string sectionRoute: modelData.route || ""
                            property string sectionTitle: modelData.title || ""
                            property string sectionIcon: modelData.icon || ""
                            property bool expandable: modelData.expandable || false
                            property string sectionStatus: modelData.status || "functional"
                            property var children: modelData.children || []
                            property int sectionOrder: modelData.order || 0
                            property bool isFixedBottom: modelData.sidebar_group === "fixed_bottom" || false

                            onIsFixedBottomChanged: {
                                if (isFixedBottom) sectionLoader.parent = fixedColumn
                            }

                            sourceComponent: Item {
                                id: groupItem
                                width: root.width
                                height: {
                                    if (isFixedBottom) return categoryItem.height
                                    if (!sectionTitle) return childrenRepeater.parent ? (categoryItem.height + childrenColumn.height) : categoryItem.height
                                    if (!expandable) return categoryItem.height
                                    var h = categoryItem.height
                                    if (children.length > 0 && root.isGroupExpanded(sectionRoute)) {
                                        h += childrenColumn.height
                                    }
                                    return h
                                }

                                                Rectangle {
                                                    id: categoryItem
                                                    width: root.width
                                                    height: root.collapsed ? 48 : 44
                                                    color: root.isParentActive(sectionRoute) && !root.collapsed
                                                        ? Qt.rgba(143/255, 183/255, 1.0, 0.08)
                                                        : "transparent"
                                                    radius: MichiTheme.radius.sm

                                                    RowLayout {
                                                        anchors.fill: parent
                                                        anchors.leftMargin: root.collapsed ? 10 : MichiTheme.spacing.md
                                                        anchors.rightMargin: root.collapsed ? 10 : MichiTheme.spacing.sm
                                                        spacing: MichiTheme.spacing.sm

                                                        Item {
                                                            Layout.preferredWidth: root.collapsed ? 44 : 20
                                                            Layout.preferredHeight: root.collapsed ? 44 : 20
                                                            Layout.alignment: Qt.AlignVCenter

                                                            Image {
                                                                anchors.centerIn: parent
                                                                width: 20; height: 20
                                                                source: root.getIconPath(sectionIcon)
                                                                sourceSize.width: 20; sourceSize.height: 20
                                                                fillMode: Image.PreserveAspectFit
                                                                opacity: root.isParentActive(sectionRoute) ? 1.0 : 0.82
                                                            }

                                                            TapHandler {
                                                                onTapped: root.routeRequested(sectionRoute)
                                                            }
                                                        }

                                                        Text {
                                                            text: sectionTitle
                                                            color: root.isParentActive(sectionRoute)
                                                                ? MichiTheme.colors.textPrimary
                                                                : MichiTheme.colors.textSecondary
                                                            font.pixelSize: MichiTheme.typography.bodySize
                                                            font.weight: root.isParentActive(sectionRoute)
                                                                ? MichiTheme.typography.weightMedium
                                                                : MichiTheme.typography.weightNormal
                                                            elide: Text.ElideRight
                                                            Layout.fillWidth: true
                                                            visible: !root.collapsed
                                                        }

                                                        Item {
                                                            Layout.preferredWidth: 20
                                                            Layout.preferredHeight: 20
                                                            visible: expandable && !root.collapsed && children.length > 0

                                                            Text {
                                                                anchors.centerIn: parent
                                                                text: root.isGroupExpanded(sectionRoute) ? "▾" : "▸"
                                                                color: MichiTheme.colors.textMuted
                                                                font.pixelSize: 10
                                                            }

                                                            TapHandler {
                                                                onTapped: root.toggleGroup(sectionRoute)
                                                            }
                                                        }

                                                        ToolTip {
                                                            visible: root.collapsed && categoryTapHandler.hovered
                                                            text: sectionTitle
                                                            delay: 600
                                                        }
                                                    }

                                                    TapHandler {
                                                        id: categoryTapHandler
                                                        onTapped: {
                                                            if (root.collapsed && expandable && children.length > 0) {
                                                                root.toggleGroup(sectionRoute)
                                                            }
                                                            root.routeRequested(sectionRoute)
                                                        }
                                                    }
                                                }

                                Column {
                                    id: childrenColumn
                                    width: root.width
                                    visible: expandable && children.length > 0
                                        && root.isGroupExpanded(sectionRoute) && !root.collapsed
                                    anchors.top: categoryItem.bottom

                                    Repeater {
                                        id: childrenRepeater
                                        model: children
                                        delegate: Item {
                                            width: root.width
                                            height: 38

                                            property var childData: modelData
                                            property string childRoute: modelData.route || ""
                                            property string childTitle: modelData.title || ""
                                            property string childIcon: modelData.icon || ""
                                            property string childStatus: modelData.status || "functional"

                                            Rectangle {
                                                width: parent.width - 16
                                                height: parent.height - 2
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                anchors.verticalCenter: parent.verticalCenter
                                                radius: MichiTheme.radius.sm
                                                color: currentRoute === childRoute
                                                    ? MichiTheme.colors.accentSelection
                                                    : "transparent"

                                                Rectangle {
                                                    visible: currentRoute === childRoute
                                                    width: 2; height: 16
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

                                                    Item {
                                                        Layout.preferredWidth: 16
                                                        Layout.preferredHeight: 16
                                                        Layout.alignment: Qt.AlignVCenter

                                                        Image {
                                                            anchors.centerIn: parent
                                                            width: 16; height: 16
                                                            source: root.getIconPath(childIcon)
                                                            sourceSize.width: 16; sourceSize.height: 16
                                                            fillMode: Image.PreserveAspectFit
                                                            opacity: currentRoute === childRoute ? 1.0 : 0.78
                                                        }
                                                    }

                                                    Text {
                                                        text: childTitle
                                                        color: currentRoute === childRoute
                                                            ? MichiTheme.colors.textPrimary
                                                            : MichiTheme.colors.textSecondary
                                                        font.pixelSize: MichiTheme.typography.bodySize - 1
                                                        font.weight: currentRoute === childRoute
                                                            ? MichiTheme.typography.weightMedium
                                                            : MichiTheme.typography.weightNormal
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }

                                                    StatusBadge {
                                                        visible: childStatus !== "functional"
                                                        text: childStatus === "planned" ? qsTr("Planificado")
                                                            : childStatus === "experimental" ? qsTr("Experimental")
                                                            : childStatus === "partial" ? qsTr("Parcial")
                                                            : childStatus === "configuration_required" ? qsTr("Configurar")
                                                            : ""
                                                        kind: childStatus === "planned" ? "neutral"
                                                            : childStatus === "experimental" ? "info"
                                                            : childStatus === "configuration_required" ? "warning"
                                                            : "neutral"
                                                    }
                                                }

                                                TapHandler {
                                                    onTapped: root.routeRequested(childRoute)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item { width: 1; height: MichiTheme.spacing.md }
                }
            }

            Column {
                id: fixedColumn
                Layout.fillWidth: true
                spacing: 0
            }
        }
    }

    Component.onCompleted: {
        autoExpandForRoute(currentRoute)
    }
}
