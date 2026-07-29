import QtQuick
import QtQuick.Layouts
import "../../components"
import "../../theme"

LibrarySectionPage {
    id: root
    objectName: "libraryCollectionsPage"
    sectionTitle: qsTr("Colecciones")
    sectionSubtitle: qsTr("Accesos dinámicos construidos desde tu biblioteca")
    sectionIcon: "library"
    navigationIndex: 6

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var customCollections: []
    readonly property var predefinedCollections: [
        { title: qsTr("Favoritos"), description: qsTr("Tu música marcada como favorita"), route: "library.favorites", icon: "songs" },
        { title: qsTr("Recientes"), description: qsTr("Incorporaciones y escuchas recientes"), route: "library.recent", icon: "songs" },
        { title: qsTr("Más reproducidas"), description: qsTr("Las canciones que más escuchas"), route: "library.most_played", icon: "songs" },
        { title: qsTr("Sin reproducir"), description: qsTr("Música pendiente de descubrir"), route: "library.unplayed", icon: "songs" },
        { title: qsTr("Años y décadas"), description: qsTr("Explora la colección cronológicamente"), route: "library.years", icon: "albums" },
        { title: qsTr("Archivos faltantes"), description: qsTr("Contenido indexado que ya no está disponible"), route: "library.missing", icon: "folders" }
    ]
    readonly property var collections: root.predefinedCollections.concat(
        root.customCollections.map(function(collection) {
            return {
                title: collection.name,
                description: qsTr("%1 reglas · %2").arg(collection.rules.length).arg(collection.logic),
                icon: "library",
                custom: true,
                definition: collection
            }
        })
    )
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

    function reloadCollections() {
        root.customCollections = root.lib && root.lib.getCollections
                                 ? root.lib.getCollections() || [] : []
    }

    function saveCollection(collection) {
        if (root.lib && root.lib.createCollection) {
            var result = root.lib.createCollection(
                        collection.name,
                        JSON.stringify(collection.rules),
                        collection.logic)
            if (!result || !result.ok)
                return
            root.reloadCollections()
            return
        }
        var entries = root.customCollections.slice()
        entries.push(collection)
        root.customCollections = entries
    }

    function deleteCollection(collectionId) {
        if (!root.lib || !root.lib.deleteCollection)
            return
        var result = root.lib.deleteCollection(collectionId)
        if (result && result.ok)
            root.reloadCollections()
    }

    function openCollection(collection) {
        if (!root.lib || !root.lib.queryCollection)
            return
        var result = root.lib.queryCollection(collection.id, 250, 0)
        if (result && result.ok)
            root.collectionSelected(collection, result)
    }

    signal collectionSelected(var collection, var result)

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.lg

        RowLayout {
            width: parent.width

            Text {
                Layout.fillWidth: true
                text: qsTr("Colecciones inteligentes")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            MichiButton {
                objectName: "createCollectionButton"
                text: qsTr("Crear colección")
                onClicked: collectionEditor.openFor(null)
            }
        }

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
                        if (modelData.custom) {
                            root.openCollection(modelData.definition)
                        } else if (typeof navigationBridge !== "undefined") {
                            navigationBridge.navigate(modelData.route)
                        }
                    }
                }
            }
        }
    }

    CollectionEditorDialog {
        id: collectionEditor
        parent: root
        onCollectionSaved: function(collection) { root.saveCollection(collection) }
    }

    Component.onCompleted: root.reloadCollections()
}
