import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Result Section"
    objectName: "searchResultSection"
    focus: true
    id: root

    property string sectionType: ""
    property string sectionTitle: ""
    property var sectionItems: []
    property int resultCount: 0
    property bool isLoading: false
    property bool sectionEmpty: false
    property var bridge: null

    signal itemClicked(string type, string id, string title, string subtitle)
    signal retryRequested()

    implicitHeight: sectionColumn.height



    function getTypeIcon() {
        switch (root.sectionType) {
            case "track": return "\u266A"
            case "album": return "\u25C9"
            case "artist": return "\u266B"
            case "playlist": return "\u2630"
            case "folder": return "\u25A0"
            case "genre": return "\u266C"
            case "radio": return "\u25E2"
            case "device": return "\u25D8"
            case "server": return "\u25CB"
            case "action": return "\u2192"
            case "setting": return "\u2699"
            default: return "\u25CF"
        }
    }

    Column {
        id: sectionColumn
        width: parent.width
        spacing: MichiTheme.spacing.xs

        Item {
            width: parent.width
            height: 28

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.getTypeIcon()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    Accessible.role: Accessible.Graphic
                    Accessible.name: root.sectionType === "track" ? "Canción" : root.sectionType === "album" ? "Álbum" : root.sectionType === "artist" ? "Artista" : root.sectionType === "playlist" ? "Lista" : root.sectionType === "folder" ? "Carpeta" : root.sectionType === "genre" ? "Género" : root.sectionType === "radio" ? "Radio" : root.sectionType === "device" ? "Dispositivo" : root.sectionType === "server" ? "Servidor" : root.sectionType === "action" ? "Acción" : root.sectionType === "setting" ? "Ajuste" : "Tipo"
                }
                Text {
                    text: root.sectionTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("(%1)").arg(root.resultCount)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.resultCount > 0 && !root.isLoading
            }
        }

        Loader {
            width: parent.width
            sourceComponent: {
                if (root.isLoading) return loadingComp
                if (root.sectionEmpty) return emptyComp
                return listComp
            }
        }

        Component {
            id: loadingComp
            LoadingState {
                title: qsTr("Buscando...")
                message: ""
                width: parent.width
            }
        }

        Component {
            id: emptyComp
            EmptyState {
                title: ""
                subtitle: qsTr("Sin resultados")
                width: parent.width
            }
        }

        Component {
            id: listComp
            Column {
                width: parent.width
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.sectionItems

                    SearchResultRow {
                        width: parent.width
                        rowType: modelData.type || root.sectionType
                        rowId: modelData.id || ""
                        rowTitle: modelData.title || ""
                        rowSubtitle: modelData.subtitle || ""
                        bridge: root.bridge
                        onClicked: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                        Keys.onReturnPressed: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                        Keys.onSpacePressed: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                    }
                }
            }
        }
    }
}
