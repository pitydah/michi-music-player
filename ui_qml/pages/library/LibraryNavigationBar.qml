import QtQuick
import "../../components"

Item {
    id: root
    objectName: "libraryNavigationBar"

    property int currentIndex: 0
    readonly property var sections: [
        { title: qsTr("Canciones"), route: "library.songs" },
        { title: qsTr("Álbumes"), route: "library.albums" },
        { title: qsTr("Artistas"), route: "library.artists" },
        { title: qsTr("Géneros"), route: "library.genres" },
        { title: qsTr("Compositores"), route: "library.composers" },
        { title: qsTr("Carpetas"), route: "library.folders" },
        { title: qsTr("Colecciones"), route: "library.collections" }
    ]

    signal sectionRequested(int index, string route)

    implicitHeight: navigationTabs.implicitHeight

    MichiTabBar {
        id: navigationTabs
        anchors.fill: parent
        model: root.sections.map(function(section) { return section.title })
        currentIndex: root.currentIndex
        accessibleName: qsTr("Secciones de Biblioteca")
        onActivated: function(index) {
            root.sectionRequested(index, root.sections[index].route)
        }
    }
}
