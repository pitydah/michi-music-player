import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string sectionType: ""
    property string sectionTitle: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property var sectionItems: []
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
    property int resultCount: 0
    property bool isLoading: false
    property bool sectionEmpty: false
    property var bridge: null

    signal itemClicked(string type, string id, string title, string subtitle)
    signal retryRequested()

    implicitHeight: sectionColumn.height

    objectName: "searchResultSection_" + sectionType

    Accessible.role: Accessible.Grouping
    Accessible.name: sectionTitle + " - " + (resultCount > 0 ? resultCount + " resultados" : "sin resultados")

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
            objectName: root.objectName + "_header"
            Accessible.role: Accessible.Heading
            Accessible.name: root.sectionTitle

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.getTypeIcon()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
    property var sectionItems: []
    property int resultCount: 0
    property bool isLoading: false
    property bool sectionEmpty: false
    property var bridge: null

    signal itemClicked(string type, string id, string title, string subtitle)
    signal retryRequested()

    implicitHeight: sectionColumn.height

    objectName: "searchResultSection_" + sectionType

    Accessible.role: Accessible.Grouping
    Accessible.name: sectionTitle + " - " + (resultCount > 0 ? resultCount + " resultados" : "sin resultados")

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
            objectName: root.objectName + "_header"
            Accessible.role: Accessible.Heading
            Accessible.name: root.sectionTitle

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.getTypeIcon()
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
                text: "(" + root.resultCount + ")"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.resultCount > 0 && !root.isLoading
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }

        Loader {
            width: parent.width
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            sourceComponent: {
                if (root.isLoading) return loadingComp
                if (root.sectionEmpty) return emptyComp
                return listComp
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            height: active ? childrenRect.height : 0
            active: isError

            sourceComponent: Item {
                implicitHeight: 40
                Row {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "\u26A0"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: errorMessage !== "" ? errorMessage : "Error al cargar"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    MichiButton {
                        text: "Reintentar"
                        variant: "ghost"
                        implicitHeight: 28
                        onClicked: root.retryRequested()
                    }
                }
>>>>>>> Stashed changes
            }
        }

        Component {
            id: loadingComp
            LoadingState {
                title: "Buscando..."
                message: ""
                width: parent.width
                objectName: root.objectName + "_loading"
                Accessible.name: "Cargando resultados para " + root.sectionTitle
            }
        }

<<<<<<< Updated upstream
=======
        Text {
            width: parent.width
            visible: !loading && !isError && items.length === 0
            text: "Sin resultados"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            objectName: "searchResultSection.empty." + sectionType
=======
            sourceComponent: {
                if (root.isLoading) return loadingComp
                if (root.sectionEmpty) return emptyComp
                return listComp
            }
        }

        Component {
            id: loadingComp
            LoadingState {
                title: "Buscando..."
                message: ""
                width: parent.width
                objectName: root.objectName + "_loading"
                Accessible.name: "Cargando resultados para " + root.sectionTitle
            }
        }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        Component {
            id: emptyComp
            EmptyState {
                title: ""
                subtitle: "Sin resultados"
                width: parent.width
                objectName: root.objectName + "_empty"
                Accessible.name: "Sin resultados para " + root.sectionTitle
            }
        }

        Component {
            id: listComp
            Column {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                objectName: root.objectName + "_list"

                Repeater {
                    model: root.sectionItems

                    SearchResultRow {
                        width: parent.width
                        rowType: modelData.type || root.sectionType
                        rowId: modelData.id || ""
                        rowTitle: modelData.title || ""
                        rowSubtitle: modelData.subtitle || ""
                        bridge: root.bridge
                        objectName: root.objectName + "_row_" + index
                        Accessible.name: (modelData.title || "Resultado") + " - " + (root.sectionTitle || "")
                        onClicked: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                        Keys.onReturnPressed: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                        Keys.onSpacePressed: root.itemClicked(modelData.type || root.sectionType, modelData.id || "", modelData.title || "", modelData.subtitle || "")
                    }
                }
            }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
