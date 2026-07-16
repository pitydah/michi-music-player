import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata"
    objectName: "metadataPage"
    focus: true
    id: root

    property var mb: typeof metadataBridge !== "undefined" ? metadataBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _mode: "single"
    property string _selectedFile: ""
    property var _selectedFiles: []
    property string pageState: "LOADING"

    Accessible.description: "Gestiona los metadatos de tus archivos de audio"

    Component.onCompleted: {
        if (root.mb && root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
            root._selectedFile = root.sel.selectedFilepath
            root._mode = "single"
            root.mb.loadMetadata(root._selectedFile)
            pageState = "EDITING"
        } else {
            pageState = "EDITING"
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Keys.onEscapePressed: {
            root._selectedFile = ""
            root._selectedFiles = []
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Editor de metadatos"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    text: pageState === "LOADING" ? "Cargando..." :
                          pageState === "APPLYING" ? "Aplicando cambios..." :
                          pageState === "ERROR" ? "Error" :
                          pageState === "EDITING" && root._selectedFile !== "" ? "Editando" : "Listo"
                    kind: pageState === "ERROR" ? "error" :
                          pageState === "APPLYING" ? "warning" :
                          pageState === "EDITING" ? "info" : "success"
                    visible: pageState !== "READY" || root._selectedFile !== ""
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: "Edición individual"
                    variant: root._mode === "single" ? "primary" : "ghost"
                    onClicked: {
                        root._mode = "single"
                        if (root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
                            root._selectedFile = root.sel.selectedFilepath
                            if (root.mb) root.mb.loadMetadata(root._selectedFile)
                        }
                    }
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                }
                MichiButton {
                    text: "Edición por lotes"
                    variant: root._mode === "batch" ? "primary" : "ghost"
                    onClicked: { root._mode = "batch" }
                }
            }

            Loader {
                width: parent.width
                sourceComponent: root._mode === "single" ? singleEditorComp : batchEditorComp
            }

            MetadataWriteProgress {
                width: parent.width
                mb: root.mb
            }

            Text {
                text: root.mb && root.mb.errorMessage ? "Error: " + root.mb.errorMessage : ""
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }
        }
    }

    Component {
        MetadataSingleEditor {
            width: parent.width
            mb: root.mb
            selectedFile: root._selectedFile
        }
    }

    Component {
        MetadataBatchEditor {
            width: parent.width
            mb: root.mb
            selectedFiles: root._selectedFiles
        }
    }

    Connections {
        target: root.mb
        function onDataChanged() {
            if (root.mb && root.mb.errorMessage !== "") {
                pageState = "ERROR"
            } else if (root.mb && root.mb.hasSelection) {
                pageState = "EDITING"
            } else {
                pageState = "READY"
            }
        }
        function onStatusChanged(status) {
            if (status === "APPLYING" || status === "BACKING_UP" || status === "WRITING" || status === "VERIFYING") {
                pageState = "APPLYING"
            } else if (status === "SUCCEEDED") {
                pageState = "EDITING"
            } else if (status === "FAILED" || status === "ERROR") {
                pageState = "ERROR"
            } else {
                pageState = "READY"
            }
        }
    }
}
