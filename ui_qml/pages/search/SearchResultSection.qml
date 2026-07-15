import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string sectionType: ""
    property string sectionTitle: ""
    property int resultCount: 0
    property var items: []
    property bool loading: false
    property bool isError: false
    property string errorMessage: ""
    property var bridge: null

    signal itemClicked(string type, string id, string title, var data)
    signal retryRequested()
    signal activateRequested()

    implicitHeight: childrenRect.height
    objectName: "searchResultSection." + sectionType

    Accessible.role: Accessible.Grouping
    Accessible.name: sectionTitle + " - " + resultCount + " resultados"

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader {
            text: sectionTitle + (resultCount > 0 ? " (" + resultCount + ")" : "")
            width: parent.width
            objectName: "searchResultSection.header." + sectionType
        }

        Loader {
            width: parent.width
            height: active ? childrenRect.height : 0
            active: loading

            sourceComponent: Item {
                implicitHeight: 40
                Row {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md

                    BusyIndicator {
                        running: true
                        implicitWidth: 20
                        implicitHeight: 20
                    }
                    Text {
                        text: "Buscando..."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        Loader {
            width: parent.width
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
            }
        }

        Repeater {
            model: loading || isError ? 0 : root.items

            SearchResultRow {
                width: parent.width
                resultType: modelData.type || ""
                resultId: modelData.id || ""
                resultTitle: modelData.title || ""
                resultSubtitle: modelData.subtitle || ""
                resultSection: root.sectionType
                resultScore: modelData.score || 0.0
                bridge: root.bridge
                objectName: "searchResultRow." + root.sectionType + "." + index

                onClicked: root.itemClicked(modelData.type || "", modelData.id || "", modelData.title || "", modelData)
                onPlayRequested: root.itemClicked(modelData.type || "", modelData.id || "", modelData.title || "", modelData)
                onActivateRequested: root.activateRequested()
            }
        }

        Text {
            width: parent.width
            visible: !loading && !isError && items.length === 0
            text: "Sin resultados"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            objectName: "searchResultSection.empty." + sectionType
        }
    }
}
