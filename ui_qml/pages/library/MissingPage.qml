import QtQuick

LibraryTrackCollectionPage {
    id: root
    objectName: "missingPage"
    focus: true
    sectionTitle: qsTr("Archivos faltantes")
    sectionSubtitle: qsTr("Contenido indexado que ya no está disponible")
    sectionIcon: "library_health"
    navigationIndex: 6

    function reloadCollection() {
        if (root.lib && root.lib.setMissingFilter)
            root.lib.setMissingFilter()
    }
}
