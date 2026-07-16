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

                Row { anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.xs
                    Text { text: "M"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightBold; height: 36 }
                    Text { text: "P"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightBold; height: 36 }
                }
                Text { anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.lg; text: "Music Player"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; height: 18; visible: !root.collapsed }
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
                            iconText: model.glyph
                            label: model.label
                            active: root.currentRoute === model.route
                            collapsed: root.collapsed
                            onClicked: root.routeRequested(model.route)
                        }
                    }
                }
            }

            Item { height: MichiTheme.spacing.xl; width: 1 }

            StatusBadge {
                anchors.left: parent.left
                anchors.leftMargin: collapsed ? (parent.width - implicitWidth) / 2 : MichiTheme.spacing.lg
                text: collapsed ? "E" : "Experimental"
                kind: "experimental"
                objectName: "statusBadge"
                Accessible.name: "Estado: Experimental"
            }

            Item { id: collapseItem; width: parent.width; height: 40
                Rectangle { id: collapseBg; anchors.centerIn: parent; width: 28; height: 28; radius: MichiTheme.radiusPill
                    color: collapseBtn.containsMouse ? Qt.rgba(1,1,1,0.08) : "transparent"
                    border.width: collapseBtn.activeFocus ? MichiTheme.focusWidth : 0
                    border.color: MichiTheme.colors.borderFocus
                    Behavior on color { ColorAnimation { duration: MichiTheme.motion.fast } }
                    Text { anchors.centerIn: parent; text: root.collapsed ? ">" : "<"; color: MichiTheme.colors.textMuted; font.pixelSize: 14; font.weight: MichiTheme.typography.weightBold }
                    MouseArea { id: collapseBtn; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.collapsed = !root.collapsed }
                }
                Accessible.role: Accessible.Button
                Accessible.name: root.collapsed ? "Expandir sidebar" : "Colapsar sidebar"
                Accessible.onPressAction: root.collapsed = !root.collapsed
            }
        }
    }

    ListModel { id: fullModel
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; glyph: "IN"; label: "Inicio" }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; glyph: "BL"; label: "Biblioteca" }
        ListElement { route: "mix"; iconSource: "icons/sidebar_mix.svg"; glyph: "MX"; label: "Mix" }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; glyph: "RP"; label: "Reproducción" }
        ListElement { route: "connections"; iconSource: "icons/sidebar_servers.svg"; glyph: "SV"; label: "Conexiones" }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; glyph: "RD"; label: "Radio" }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; glyph: "PL"; label: "Playlists" }
        ListElement { route: "home_audio"; iconSource: "icons/sidebar_home_audio.svg"; glyph: "HA"; label: "Home Audio" }
        ListElement { route: "assistant"; iconSource: "icons/sidebar_assistant.svg"; glyph: "AI"; label: "Michi AI" }
        ListElement { route: "audio_lab"; iconSource: "icons/sidebar_audio_lab.svg"; glyph: "AL"; label: "Audio Lab" }
    }

    ListModel { id: deliveryModel
        ListElement { route: "home"; iconSource: "icons/sidebar_home.svg"; glyph: "IN"; label: "Inicio" }
        ListElement { route: "library"; iconSource: "icons/sidebar_library.svg"; glyph: "BL"; label: "Biblioteca" }
        ListElement { route: "playback"; iconSource: "icons/sidebar_songs.svg"; glyph: "RP"; label: "Reproducción" }
        ListElement { route: "playlists"; iconSource: "icons/sidebar_playlists.svg"; glyph: "PL"; label: "Playlists" }
        ListElement { route: "radio"; iconSource: "icons/sidebar_radio.svg"; glyph: "RD"; label: "Radio" }
        ListElement { route: "settings"; iconSource: "icons/sidebar_servers.svg"; glyph: "SV"; label: "Ajustes" }
        ListElement { route: "diagnostics"; iconSource: "icons/sidebar_home_audio.svg"; glyph: "DG"; label: "Diagnóstico" }
    }
}
