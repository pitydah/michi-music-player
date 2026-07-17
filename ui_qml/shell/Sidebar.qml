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

    MichiResponsive { id: responsive; availableWidth: root.width }
    property bool collapsed: responsive.sidebarAutoCollapse

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

            Rectangle { width: collapsed ? parent.width * 0.4 : parent.width - MichiTheme.spacing.xl * 2; height: 1; color: MichiTheme.colors.borderSubtle; anchors.horizontalCenter: parent.horizontalCenter }

            Flickable {
                width: parent.width; height: Math.min(contentHeight, parent.height - 180)
                contentHeight: navColumn.height + MichiTheme.spacing.lg; clip: true
                boundsBehavior: Flickable.StopAtBounds; interactive: contentHeight > height

                Column {
                    id: navColumn
                    anchors.left: parent.left; anchors.right: parent.right
                    topPadding: MichiTheme.spacing.sm; spacing: 2

                    Repeater {
                        model: root.deliveryMode ? deliveryModel : fullModel

                        SidebarItem {
                            iconSource: Qt.resolvedUrl("../../" + model.iconSource)
                            label: model.label
                            active: root.currentRoute === model.route
                            collapsed: root.collapsed
                            onClicked: root.routeRequested(model.route)
                            StatusBadge {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: model.notificationCount > 0 ? model.notificationCount : ""
                                kind: "info"
                                visible: model.notificationCount > 0
                            }
                        }
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
                    MouseArea { id: collapseBtn; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.collapsed = !root.collapsed }
                }
                Accessible.role: Accessible.Button
                Accessible.name: root.collapsed ? "Expandir sidebar" : "Colapsar sidebar"
                Accessible.onPressAction: root.collapsed = !root.collapsed
            }
        }
    }

    ListModel { id: fullModel
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0 }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0 }
        ListElement { route: "mix"; iconSource: "icons/sidebar_mix.svg"; label: "Mix"; notificationCount: 0 }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0 }
        ListElement { route: "connections"; iconSource: "icons/sidebar_servers.svg"; label: "Conexiones"; notificationCount: 0 }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0 }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0 }
        ListElement { route: "home_audio"; iconSource: "icons/sidebar_home_audio.svg"; label: "Audio del Hogar"; notificationCount: 0 }
        ListElement { route: "assistant"; iconSource: "icons/sidebar_assistant.svg"; label: "Michi IA"; notificationCount: 0 }
        ListElement { route: "audio_lab"; iconSource: "icons/sidebar_audio_lab.svg"; label: "Audio Lab"; notificationCount: 0 }
    }

    ListModel { id: deliveryModel
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0 }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0 }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0 }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0 }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0 }
        ListElement { route: "settings"; iconSource: "icons/sidebar_home.svg"; label: "Ajustes"; notificationCount: 0 }
        ListElement { route: "diagnostics"; iconSource: "icons/sidebar_identifier.svg"; label: "Diagnóstico"; notificationCount: 0 }
    }
}
