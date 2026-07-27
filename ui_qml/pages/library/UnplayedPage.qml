import QtQuick

LibraryTrackCollectionPage {
    id: root
    objectName: "unplayedPage"
    focus: true
    sectionTitle: qsTr("Sin reproducir")
    sectionSubtitle: qsTr("Música pendiente de descubrir")
    sectionIcon: "songs"
    navigationIndex: 6

    function reloadCollection() {
        if (root.lib && root.lib.setUnplayedFilter)
            root.lib.setUnplayedFilter()
    }
}
