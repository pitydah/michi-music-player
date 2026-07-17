import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Input Selection"
    objectName: "audioInputSelection"
    focus: true
    id: root

    property var selCtx: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property var libBridge: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null

    property var selectedFiles: []
    property var recentFiles: []
    property int totalSize: 0
    property var formatCounts: ({})
    property int state: 0

    signal filesSelected(var filepaths)
    signal filesCleared()


    readonly property int stateEmpty: 0
    readonly property int stateHasFiles: 1
    readonly property int stateLoadingMetadata: 2

    function _updateFileInfo(files) {
        root.selectedFiles = files
        var size = 0
        var formats = {}
        for (var i = 0; i < files.length; i++) {
            var f = files[i]
            if (typeof f === "string") {
                formats["unknown"] = (formats["unknown"] || 0) + 1
            } else {
                size += f.size || 0
                var ext = (f.name || f.filepath || "").split(".").pop().toUpperCase()
                formats[ext] = (formats[ext] || 0) + 1
            }
        }
        root.totalSize = size
        root.formatCounts = formats
        root.state = files.length > 0 ? root.stateHasFiles : root.stateEmpty
        root.filesSelected(files)
    }

    function addFiles(files) {
        _updateFileInfo(files)
    }

    function clearFiles() {
        root.selectedFiles = []
        root.totalSize = 0
        root.formatCounts = ({})
        root.state = root.stateEmpty
        root.filesCleared()
    }

    function removeFile(index) {
        var files = root.selectedFiles.slice()
        files.splice(index, 1)
        _updateFileInfo(files)
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        Text {
            text: "Selección de entrada"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
        }

        Row {
            spacing: MichiTheme.spacing.sm
            MichiButton {
                Accessible.role: Accessible.Button

                text: "Desde biblioteca"
                variant: "secondary"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("library")
                }
            }
                Accessible.role: Accessible.Button

            MichiButton {
                text: "Seleccionar archivos"
                variant: "secondary"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root.libBridge && root.libBridge.selectFiles)
                        root.libBridge.selectFiles()
                }
                Accessible.role: Accessible.Button

            }
            MichiButton {
                text: "Pegar ruta"
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.sm; variant: "base"
            visible: root.state === root.stateEmpty
            height: 60
            Text {
                anchors.centerIn: parent
                text: "Arrastra archivos aquí o usa los botones de selección"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.sm; variant: "primary"
            visible: root.state === root.stateLoadingMetadata
            height: 60
            Row {
                anchors.centerIn: parent; spacing: MichiTheme.spacing.sm
                BusyIndicator { running: true; width: 20; height: 20 }
                Text { text: "Cargando metadatos..."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.sm; variant: "primary"
            visible: root.state === root.stateHasFiles
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.xs
                Text {
                    text: root.selectedFiles.length + " archivo(s) seleccionados"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                }
                Text {
                    text: "Tamaño total: " + (root.totalSize > 1048576 ? (root.totalSize / 1048576).toFixed(1) + " MB" : (root.totalSize / 1024).toFixed(1) + " KB")
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; visible: root.totalSize > 0
                }
                Row {
                    spacing: MichiTheme.spacing.sm; visible: true
                    Repeater {
                        model: Object.keys(root.formatCounts)
                        StatusBadge {
                            text: modelData + ": " + root.formatCounts[modelData]
                            kind: "info"
                        }
                    }
                }
            }
        }

        Repeater {
            model: root.state === root.stateHasFiles ? root.selectedFiles : []

            GlassMaterial {
                width: parent.width; height: 36; radius: MichiTheme.radius.sm; variant: "base"
                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                    Text {
                        width: parent.width - 60
                        text: typeof modelData === "string" ? modelData : modelData.name || modelData.filepath || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                        Accessible.role: Accessible.Button

                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    MichiButton {
                        text: "x"; variant: "ghost"; implicitWidth: 32; implicitHeight: 24
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: root.removeFile(index)
                    }
                }
            Accessible.role: Accessible.Button

            }
        }

        MichiButton {
            text: "Limpiar selección"
            variant: "ghost"
            visible: root.state === root.stateHasFiles
            activeFocusOnTab: true
            Keys.onReturnPressed: onClicked()
            Keys.onSpacePressed: onClicked()
            onClicked: root.clearFiles()
        }
    }
}
