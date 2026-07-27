import QtQuick

LibraryTrackCollectionPage {
    id: root
    objectName: "mostPlayedPage"
    focus: true
    sectionTitle: qsTr("Más reproducidas")
    sectionSubtitle: qsTr("Las canciones que más escuchas")
    sectionIcon: "songs"
    navigationIndex: 6

    function reloadCollection() {
        if (root.lib && root.lib.trackModel)
            root.lib.trackModel.refreshForSort("play_count", false)
    }
}
