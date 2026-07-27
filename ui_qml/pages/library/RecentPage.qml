import QtQuick

LibraryTrackCollectionPage {
    id: root
    objectName: "recentPage"
    focus: true
    sectionTitle: qsTr("Recientes")
    sectionSubtitle: qsTr("Incorporaciones recientes de tu biblioteca")
    sectionIcon: "history"
    navigationIndex: 6

    function reloadCollection() {
        if (root.lib && root.lib.trackModel)
            root.lib.trackModel.refreshForSort("date_added", false)
    }
}
