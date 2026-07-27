import QtQuick
import "../../components"
import "../../theme"

LibrarySectionPage {
    id: root
    objectName: "libraryCollectionsPage"
    sectionTitle: qsTr("Colecciones")
    sectionSubtitle: qsTr("Accesos dinámicos construidos desde tu biblioteca")
    sectionIcon: "library"
    navigationIndex: 6

    readonly property var collections: [
        { title: qsTr("Favoritos"), description: qsTr("Tu música marcada como favorita"), route: "library.favorites", icon: "songs" },
        { title: qsTr("Recientes"), description: qsTr("Incorporaciones y escuchas recientes"), route: "library.recent", icon: "songs" },
        { title: qsTr("Más reproducidas"), description: qsTr("Las canciones que más escuchas"), route: "library.most_played", icon: "songs" },
        { title: qsTr("Sin reproducir"), description: qsTr("Música pendiente de descubrir"), route: "library.unplayed", icon: "songs" },
        { title: qsTr("Años y décadas"), description: qsTr("Explora la colección cronológicamente"), route: "library.years", icon: "albums" },
        { title: qsTr("Archivos faltantes"), description: qsTr("Contenido indexado que ya no está disponible"), route: "library.missing", icon: "folders" }
    ]
    readonly property var visibleCollections: root.filteredCollections(
                                                  root.collections,
                                                  root.headerSearchText
                                              )
    headerSearchPlaceholder: qsTr("Buscar colecciones…")
    headerRefreshEnabled: false
    headerStatusText: qsTr("%1 colecciones").arg(root.visibleCollections.length)

    function filteredCollections(entries, query) {
        var normalized = (query || "").trim().toLocaleLowerCase()
        if (normalized === "")
            return entries || []
        return (entries || []).filter(function(entry) {
            var haystack = (entry.title + " " + entry.description)
                           .toLocaleLowerCase()
            return haystack.indexOf(normalized) >= 0
        })
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.lg

        MichiResponsiveGrid {
            width: parent.width

            Repeater {
                model: root.visibleCollections

                MichiFeatureCard {
                    required property var modelData
                    title: modelData.title
                    description: modelData.description
                    iconKey: modelData.icon
                    route: modelData.route
                    primaryActionText: qsTr("Abrir")
                    onClicked: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate(modelData.route)
                    }
                }
            }
        }
    }
}
