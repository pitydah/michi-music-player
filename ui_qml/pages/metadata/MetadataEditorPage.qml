import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

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
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Editor de metadatos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Edición individual"
                    variant: root._mode === "single" ? "primary" : "ghost"
                    onClicked: { root._mode = "single"; root.loadFromSelection() }
                }
                MichiButton {
                    text: "Edición por lotes"
                    variant: root._mode === "batch" ? "primary" : "ghost"
                    onClicked: { root._mode = "batch" }
                }
            }

            Loader {
                width: parent.width
                sourceComponent: root._mode === "single" ? singleEditor : batchEditor
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
