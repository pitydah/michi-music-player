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
    property string pageState: "LOADING"

    objectName: "metadata.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Editor de metadatos"
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
        objectName: "metadata.flickable"

        Keys.onEscapePressed: {
            root._selectedFile = ""
            root._selectedFiles = []
        }

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                id: headerRow
                width: parent.width
                spacing: MichiTheme.spacing.sm
                objectName: "metadata.headerRow"

                Text {
                    id: titleText
                    text: "Editor de metadatos"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: "metadata.title"
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Editor de metadatos"
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    id: stateBadge
                    text: pageState === "LOADING" ? "Cargando..." :
                          pageState === "APPLYING" ? "Aplicando cambios..." :
                          pageState === "ERROR" ? "Error" :
                          pageState === "EDITING" && root._selectedFile !== "" ? "Editando" : "Listo"
                    kind: pageState === "ERROR" ? "error" :
                          pageState === "APPLYING" ? "warning" :
                          pageState === "EDITING" ? "info" : "success"
                    visible: pageState !== "READY" || root._selectedFile !== ""
                    objectName: "metadata.stateBadge"
                }
            }

            Row {
                id: modeRow
                spacing: MichiTheme.spacing.sm
                objectName: "metadata.modeRow"
                MichiButton {
                    id: singleModeBtn
                    text: "Edición individual"
                    variant: root._mode === "single" ? "primary" : "ghost"
                    objectName: "metadata.mode.single"
                    Accessible.name: "Modo edición individual"
                    Accessible.description: "Editar metadatos de una sola canción"
                    onClicked: {
                        root._mode = "single"
                        if (root.sel && root.sel.hasSelection && root.sel.selectedFilepath) {
                            root._selectedFile = root.sel.selectedFilepath
                            if (root.mb) root.mb.loadMetadata(root._selectedFile)
                        }
                    }
                }
                MichiButton {
                    id: batchModeBtn
                    text: "Edición por lotes"
                    variant: root._mode === "batch" ? "primary" : "ghost"
                    objectName: "metadata.mode.batch"
                    Accessible.name: "Modo edición por lotes"
                    Accessible.description: "Editar metadatos de múltiples canciones"
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
                id: errorText
                text: root.mb && root.mb.errorMessage ? "Error: " + root.mb.errorMessage : ""
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
                objectName: "metadata.errorText"
                Accessible.name: text
            }
        }
    }

    Component {
        id: singleEditorComp
        MetadataSingleEditor {
            width: parent.width
            mb: root.mb
            selectedFile: root._selectedFile
        }
    }

    Component {
        id: batchEditorComp
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
