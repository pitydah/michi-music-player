import QtQuick

LibraryTrackCollectionPage {
    id: root
    objectName: "favoritesPage"
    focus: true
    sectionTitle: qsTr("Favoritos")
    sectionSubtitle: qsTr("Tu música marcada para volver a escuchar")
    sectionIcon: "songs"
    navigationIndex: 6

    function reloadCollection() {
        if (root.lib && root.lib.setFavoritesFilter)
            root.lib.setFavoritesFilter()
    }
}
