import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "metadataEditor.page"
    focus: true
    Accessible.role: Accessible.Panel
    Accessible.name: "Editor de metadatos"
    Accessible.description: "Edita los metadatos de tus archivos de audio"

    property var mb: typeof metadataBridge !== "undefined" ? metadataBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _mode: "single"
    property string _selectedFile: ""
    property var _selectedFiles: []

    function loadFromSelection() {
        if (root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
            root._selectedFile = root.sel.selectedFilepath
            root._mode = "single"
            if (root.mb) root.mb.loadMetadata(root._selectedFile)
        }
    }

    Component.onCompleted: root.loadFromSelection()

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        objectName: "metadataEditor.flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg
            objectName: "metadataEditor.column"

            Text {
                id: titleText
                text: "Editor de metadatos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "metadataEditor.title"
                Accessible.role: Accessible.Heading
                Accessible.name: "Editor de metadatos"
            }

            Row {
                id: modeRow
                spacing: MichiTheme.spacing.sm
                objectName: "metadataEditor.modeRow"
                MichiButton {
                    id: singleBtn
                    text: "Edición individual"
                    variant: root._mode === "single" ? "primary" : "ghost"
                    objectName: "metadataEditor.mode.single"
                    Accessible.name: "Modo edición individual"
                    onClicked: { root._mode = "single"; root.loadFromSelection() }
                }
                MichiButton {
                    id: batchBtn
                    text: "Edición por lotes"
                    variant: root._mode === "batch" ? "primary" : "ghost"
                    objectName: "metadataEditor.mode.batch"
                    Accessible.name: "Modo edición por lotes"
                    onClicked: { root._mode = "batch" }
                }
            }

            Loader {
                id: editorLoader
                width: parent.width
                sourceComponent: root._mode === "single" ? singleEditor : batchEditor
                objectName: "metadataEditor.loader"
            }
        }
    }

    Component {
        id: singleEditor
        MetadataSingleEditor {
            width: parent.width
            mb: root.mb
            selectedFile: root._selectedFile
        }
    }

    Component {
        id: batchEditor
        MetadataBatchEditor {
            width: parent.width
            mb: root.mb
            selectedFiles: root._selectedFiles
        }
    }
}
