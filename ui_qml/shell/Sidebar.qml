import QtQuick
import QtQuick.Controls
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
    readonly property bool _autoCollapsed: parent ? parent.width < 900 : false
    property bool collapsed: _autoCollapsed || _userCollapsed

    width: collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth
    Behavior on width { NumberAnimation { duration: MichiTheme.motion.durationNormal; easing.type: Easing.OutCubic } }

    SidebarMaterial {
        anchors.fill: parent

        Column {
            anchors.fill: parent; spacing: 0

            Column {
                width: parent.width; anchors.topMargin: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.xs; topPadding: MichiTheme.spacing.xl; bottomPadding: MichiTheme.spacing.sm

                Row { anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                    Image { source: "../../icons/app_icon.svg"; sourceSize.width: 28; sourceSize.height: 28; fillMode: Image.PreserveAspectFit }
                    Column { spacing: 0; visible: !root.collapsed
                        Text { text: "Michi"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Music Player"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                }
            }

            Flickable {
                id: scrollArea
                width: parent.width
                height: Math.min(contentHeight, parent.height - 180)
                contentHeight: navColumn.height + MichiTheme.spacing.lg
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height

                Column {
                    id: navColumn
                    anchors.left: parent.left; anchors.right: parent.right
                    topPadding: MichiTheme.spacing.sm; spacing: 0

                    Repeater {
                        model: root.deliveryMode ? deliveryModel : groupedModel

                        Loader {
                            width: parent.width
                            sourceComponent: model.isSeparator ? separatorComp : itemComp
                            property var modelData: model
                        }
                    }
                }
            }

            Component {
                id: separatorComp
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.xs
                    visible: !root.collapsed

                    Text {
                        anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md
                        text: modelData.label
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightMedium
                        topPadding: MichiTheme.spacing.sm
                    }
                }
            }

            Component {
                id: itemComp
                SidebarItem {
                    iconSource: Qt.resolvedUrl("../../" + modelData.iconSource)
                    label: modelData.label
                    active: root.currentRoute === modelData.route
                    collapsed: root.collapsed
                    onClicked: root.routeRequested(modelData.route)
                    StatusBadge {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.notificationCount > 0 ? modelData.notificationCount : ""
                        kind: "info"
                        visible: modelData.notificationCount > 0
                    }
                }
            }

            Item { height: MichiTheme.spacing.xl; width: 1 }

            Item { id: collapseItem; width: parent.width; height: 40
                Rectangle { id: collapseBg; anchors.centerIn: parent; width: 28; height: 28; radius: MichiTheme.radius.pill
                    color: collapseBtn.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    border.width: collapseBtn.activeFocus ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus
                    Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
                    Image { anchors.centerIn: parent; source: "../../icons/nav_back.svg"; sourceSize.width: 14; sourceSize.height: 14; rotation: root.collapsed ? 180 : 0; fillMode: Image.PreserveAspectFit }
                    MouseArea { id: collapseBtn; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root._userCollapsed = !root._userCollapsed }
                }
                Accessible.role: Accessible.Button
                Accessible.name: root.collapsed ? "Expandir sidebar" : "Colapsar sidebar"
                Accessible.onPressAction: root._userCollapsed = !root._userCollapsed
            }
        }
    }

    ListModel { id: groupedModel
        ListElement { route: ""; iconSource: ""; label: "NAVEGACION"; notificationCount: 0; isSeparator: true }
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0; isSeparator: false }
        ListElement { route: "mix"; iconSource: "icons/sidebar_mix.svg"; label: "Mix"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0; isSeparator: false }

        ListElement { route: ""; iconSource: ""; label: "RED Y DISPOSITIVOS"; notificationCount: 0; isSeparator: true }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "connections"; iconSource: "icons/sidebar_servers.svg"; label: "Conexiones"; notificationCount: 0; isSeparator: false }
        ListElement { route: "home_audio"; iconSource: "icons/sidebar_home_audio.svg"; label: "Home Audio"; notificationCount: 0; isSeparator: false }

        ListElement { route: ""; iconSource: ""; label: "HERRAMIENTAS"; notificationCount: 0; isSeparator: true }
        ListElement { route: "audio_lab"; iconSource: "icons/sidebar_audio_lab.svg"; label: "Audio Lab"; notificationCount: 0; isSeparator: false }
        ListElement { route: "assistant"; iconSource: "icons/sidebar_assistant.svg"; label: "Michi AI"; notificationCount: 0; isSeparator: false }
    }

    ListModel { id: deliveryModel
        ListElement { route: ""; iconSource: ""; label: "NAVEGACION"; notificationCount: 0; isSeparator: true }
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0; isSeparator: false }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0; isSeparator: false }
        ListElement { route: ""; iconSource: ""; label: "SISTEMA"; notificationCount: 0; isSeparator: true }
        ListElement { route: "diagnostics"; iconSource: "icons/sidebar_identifier.svg"; label: "Diagnóstico"; notificationCount: 0; isSeparator: false }
    }
}
