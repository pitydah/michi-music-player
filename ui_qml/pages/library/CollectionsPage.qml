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

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.lg

        MichiResponsiveGrid {
            width: parent.width

            Repeater {
                model: root.collections

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
