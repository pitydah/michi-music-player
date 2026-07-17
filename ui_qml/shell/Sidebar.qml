import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"
import "../components"

Item {
    id: root
    objectName: "sidebar"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Navegación principal"

    property string currentRoute: "home"
    property bool deliveryMode: typeof appStateBridge !== "undefined" && appStateBridge
                                ? appStateBridge.deliveryMode : false
    property bool autoCollapsed: false
    property bool userCollapsed: false
    property int expandedWidth: MichiTheme.sidebarWidth
    readonly property bool collapsed: autoCollapsed || userCollapsed

    signal routeRequested(string route)

    implicitWidth: collapsed ? MichiTheme.sidebarWidthCompact : expandedWidth
    implicitHeight: 640

    Behavior on implicitWidth {
        NumberAnimation {
            duration: MichiTheme.motion.durationNormal
            easing.type: Easing.OutCubic
        }
    }

    function toggleCollapsed() {
        if (!root.autoCollapsed)
            root.userCollapsed = !root.userCollapsed
    }

    SidebarMaterial {
        anchors.fill: parent

        Column {
            anchors.fill: parent
            spacing: 0

            Item {
                width: parent.width
                height: 72

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: root.collapsed ? 20 : MichiTheme.spacing.md
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.sm

                    Image {
                        source: "../../icons/app_icon.svg"
                        sourceSize.width: 28
                        sourceSize.height: 28
                        fillMode: Image.PreserveAspectFit
                    }

                    Column {
                        spacing: 0
                        visible: !root.collapsed
                        Text {
                            text: "Michi"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }
                        Text {
                            text: "Music Player"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }

            Flickable {
                id: scrollArea
                width: parent.width
                height: Math.max(0, parent.height - 120)
                contentHeight: navColumn.height + MichiTheme.spacing.lg
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height

                Column {
                    id: navColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    topPadding: MichiTheme.spacing.sm
                    spacing: 0

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

            Item {
                id: collapseItem
                width: parent.width
                height: 48
                visible: !root.autoCollapsed
                activeFocusOnTab: visible

                Accessible.role: Accessible.Button
                Accessible.name: root.collapsed ? "Expandir barra lateral" : "Colapsar barra lateral"
                Accessible.onPressAction: root.toggleCollapsed()

                Keys.onReturnPressed: root.toggleCollapsed()
                Keys.onSpacePressed: root.toggleCollapsed()

                Rectangle {
                    anchors.centerIn: parent
                    width: 32
                    height: 32
                    radius: MichiTheme.radius.pill
                    color: collapseMouse.containsMouse || collapseItem.activeFocus
                           ? MichiTheme.colors.surfaceHover : "transparent"
                    border.width: collapseItem.activeFocus ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus

                    Behavior on color {
                        ColorAnimation { duration: MichiTheme.motion.fast }
                    }

                    Image {
                        anchors.centerIn: parent
                        source: "../../icons/nav_back.svg"
                        sourceSize.width: 14
                        sourceSize.height: 14
                        rotation: root.collapsed ? 180 : 0
                        fillMode: Image.PreserveAspectFit

                        Behavior on rotation {
                            NumberAnimation { duration: MichiTheme.motion.durationFast }
                        }
                    }

                    MouseArea {
                        id: collapseMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleCollapsed()
                    }
                }
            }
        }
    }

    Component {
        id: separatorComp
        Item {
            width: parent.width
            height: root.collapsed ? 12 : 30

            Text {
                anchors.left: parent.left
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.bottom: parent.bottom
                anchors.bottomMargin: MichiTheme.spacing.xs
                text: modelData.label
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                font.weight: MichiTheme.typography.weightMedium
                visible: !root.collapsed
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
                anchors.rightMargin: root.collapsed ? 2 : MichiTheme.spacing.xs
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.notificationCount > 0 ? modelData.notificationCount : ""
                kind: "info"
                visible: modelData.notificationCount > 0
            }
        }
    }

    ListModel {
        id: groupedModel
        ListElement { route: ""; iconSource: ""; label: "NAVEGACIÓN"; notificationCount: 0; isSeparator: true }
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0; isSeparator: false }
        ListElement { route: "mix"; iconSource: "icons/sidebar_mix.svg"; label: "Mix"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0; isSeparator: false }

        ListElement { route: ""; iconSource: ""; label: "RED Y DISPOSITIVOS"; notificationCount: 0; isSeparator: true }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "connections"; iconSource: "icons/sidebar_servers.svg"; label: "Conexiones"; notificationCount: 0; isSeparator: false }
        ListElement { route: "home_audio"; iconSource: "icons/sidebar_home_audio.svg"; label: "Audio del hogar"; notificationCount: 0; isSeparator: false }

        ListElement { route: ""; iconSource: ""; label: "HERRAMIENTAS"; notificationCount: 0; isSeparator: true }
        ListElement { route: "audio_lab"; iconSource: "icons/sidebar_audio_lab.svg"; label: "Audio Lab"; notificationCount: 0; isSeparator: false }
        ListElement { route: "assistant"; iconSource: "icons/sidebar_assistant.svg"; label: "Michi IA"; notificationCount: 0; isSeparator: false }
    }

    ListModel {
        id: deliveryModel
        ListElement { route: ""; iconSource: ""; label: "NAVEGACIÓN"; notificationCount: 0; isSeparator: true }
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; label: "Inicio"; notificationCount: 0; isSeparator: false }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; label: "Biblioteca"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; label: "Reproducción"; notificationCount: 0; isSeparator: false }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; label: "Playlists"; notificationCount: 0; isSeparator: false }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; label: "Radio"; notificationCount: 0; isSeparator: false }
        ListElement { route: ""; iconSource: ""; label: "SISTEMA"; notificationCount: 0; isSeparator: true }
        ListElement { route: "settings"; iconSource: "icons/sidebar_settings.svg"; label: "Ajustes"; notificationCount: 0; isSeparator: false }
        ListElement { route: "diagnostics"; iconSource: "icons/sidebar_identifier.svg"; label: "Diagnóstico"; notificationCount: 0; isSeparator: false }
    }
}
