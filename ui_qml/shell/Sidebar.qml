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
    readonly property bool _autoCollapsed: parent ? parent.width < 1050 : false
    property bool collapsed: _autoCollapsed || _userCollapsed

    width: collapsed ? MichiTheme.sidebarWidthCompact : MichiTheme.sidebarWidth
    Behavior on width { NumberAnimation { duration: MichiTheme.motion.durationNormal; easing.type: Easing.OutCubic } }

    SidebarMaterial {
        anchors.fill: parent

        Flickable {
            anchors.fill: parent
            contentHeight: contentColumn.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: contentColumn
                width: parent.width; spacing: 0

                Item { width: 1; height: MichiTheme.spacing.md }

                // Escuchar
                SidebarSection { text: collapsed ? "" : qsTr("ESCUCHAR"); collapsed: root.collapsed }
                SidebarItem { text: qsTr("Inicio"); route: "home"; iconSource: "../../icons/sidebar/home.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("home") }
                SidebarItem { text: qsTr("Biblioteca"); route: "library"; iconSource: "../../icons/sidebar/library.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("library") }
                SidebarItem { text: qsTr("Descubrir"); route: "mix"; iconSource: "../../icons/sidebar/mix.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("mix") }
                SidebarItem { text: qsTr("Playlists"); route: "playlists"; iconSource: "../../icons/sidebar/playlists.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("playlists") }
                SidebarItem { text: qsTr("Radio"); route: "radio"; iconSource: "../../icons/sidebar/radio.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("radio") }

                Item { width: 1; height: MichiTheme.spacing.md }

                // Ecosistema Michi
                SidebarSection { text: collapsed ? "" : qsTr("ECOSISTEMA"); collapsed: root.collapsed }
                SidebarItem { text: qsTr("Servidores"); route: "connections"; iconSource: "../../icons/sidebar/connections.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("connections") }
                SidebarItem { text: qsTr("Sincronizar"); route: "devices"; iconSource: "../../icons/sidebar/devices.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("devices") }
                SidebarItem { text: qsTr("Audio en el hogar"); route: "home_audio"; iconSource: "../../icons/sidebar/home_audio.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("home_audio") }

                Item { width: 1; height: MichiTheme.spacing.md }

                // Herramientas
                SidebarSection { text: collapsed ? "" : qsTr("HERRAMIENTAS"); collapsed: root.collapsed }
                SidebarItem { text: qsTr("Audio Lab"); route: "audio_lab"; iconSource: "../../icons/sidebar/audio_lab.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("audio_lab") }
                SidebarItem { text: qsTr("Metadatos"); route: "metadata.inspector"; iconSource: "../../icons/sidebar/metadata.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("metadata.inspector") }
                SidebarItem { text: qsTr("Library Doctor"); route: "library_doctor"; iconSource: "../../icons/sidebar/doctor.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("library_doctor") }
                SidebarItem { text: qsTr("Ecualizador"); route: "equalizer"; iconSource: "../../icons/sidebar/eq.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("equalizer") }
                SidebarItem { text: qsTr("Perfiles de salida"); route: "outputs"; iconSource: "../../icons/sidebar/outputs.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("outputs") }

                Item { width: 1; height: MichiTheme.spacing.md }

                // Accesos globales
                SidebarSection { text: collapsed ? "" : qsTr("ACCESOS"); collapsed: root.collapsed }
                SidebarItem { text: qsTr("Buscar"); route: "search"; iconSource: "../../icons/sidebar/search.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("search") }
                SidebarItem { text: "Michi AI"; route: "assistant"; iconSource: "../../icons/sidebar/ai.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("assistant") }
                SidebarItem { text: qsTr("Cola"); route: "queue"; iconSource: "../../icons/sidebar/queue.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("queue") }
                SidebarItem { text: qsTr("Historial"); route: "history"; iconSource: "../../icons/sidebar/history.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("history") }
                SidebarItem { text: qsTr("Ajustes"); route: "settings"; iconSource: "../../icons/sidebar/settings.svg"; currentRoute: root.currentRoute; collapsed: root.collapsed; onClicked: root.routeRequested("settings") }
            }
        }
    }
}
