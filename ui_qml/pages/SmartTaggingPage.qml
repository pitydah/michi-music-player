import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var stb: typeof smartTaggingBridge !== "undefined" ? smartTaggingBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string selectedFile: ""
    property string _errorMsg: ""
    property bool _confirmApply: false
    property string pageState: "LOADING"

    objectName: "smartTagging.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Smart Tagging"
    Accessible.description: "Sugerencias automáticas de metadatos para tu biblioteca musical"

    Keys.onEscapePressed: {
        root._confirmApply = false
        root._errorMsg = ""
    }

    Component.onCompleted: {
        if (root.stb) {
            if (root.stb.status === "idle") {
                pageState = "READY"
            } else if (root.stb.status === "scanning") {
                pageState = "ANALYZING"
            } else {
                pageState = "READY"
            }
        } else {
            pageState = "ERROR"
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        objectName: "smartTagging.flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                id: headerRow
                width: parent.width
                spacing: MichiTheme.spacing.sm
                objectName: "smartTagging.headerRow"

                Text {
                    id: titleText
                    text: "Smart Tagging"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: "smartTagging.title"
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Smart Tagging"
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    id: stateBadge
                    text: pageState === "ANALYZING" ? "Analizando..." :
                          pageState === "APPLYING" ? "Aplicando..." :
                          pageState === "ERROR" ? "Error" :
                          pageState === "READY" && root.stb && root.stb.status === "review" ? "Revisar" : ""
                    kind: pageState === "ERROR" ? "error" :
                          pageState === "APPLYING" ? "warning" :
                          pageState === "ANALYZING" ? "info" : "success"
                    visible: pageState !== "LOADING"
                    objectName: "smartTagging.stateBadge"
                }
            }

            HeroMaterial {
                width: parent.width; height: 100; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Etiquetado inteligente"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Sugerencias automáticas de metadatos para tu biblioteca musical."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                id: fileCard
                width: parent.width; height: 70
                title: root.selectedFile ? "Archivo seleccionado" : (root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Canción desde Biblioteca" : "Seleccionar archivo")
                subtitle: root.selectedFile ? root.selectedFile : (root.sel && root.sel.hasSelection && root.sel.selectedTitle ? root.sel.selectedTitle : "Elige un archivo de audio")
                variant: root.selectedFile || (root.sel && root.sel.hasSelection) ? "accent" : "base"
                objectName: "smartTagging.fileCard"
                Accessible.name: title
                Accessible.description: subtitle
                onClicked: fileDialog.open()
            }

            Row {
                id: fileActionRow
                spacing: MichiTheme.spacing.sm
                objectName: "smartTagging.fileActions"
                MichiButton {
                    id: selectFileBtn
                    text: root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Usar canción seleccionada" : "Seleccionar archivo"
                    variant: "primary"
                    objectName: "smartTagging.selectFile"
                    Accessible.name: text
                    Accessible.description: "Seleccionar archivo de audio para analizar"
                    onClicked: {
                        if (root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" && root.sel.selectedFilepath) {
                            root.selectedFile = root.sel.selectedFilepath
                        } else {
                            fileDialog.open()
                        }
                    }
                }
                MichiButton {
                    id: scanBtn
                    text: root.stb && root.stb.status === "scanning" ? "Cancelar" : "Escanear"
                    variant: "secondary"
                    enabled: root.selectedFile !== "" && (root.stb ? root.stb.status !== "scanning" : true)
                    objectName: "smartTagging.scanButton"
                    Accessible.name: root.stb && root.stb.status === "scanning" ? "Cancelar escaneo" : "Escanear archivo"
                    Accessible.description: root.selectedFile !== "" ? "Analizar: " + root.selectedFile : "Selecciona un archivo primero"
                    onClicked: {
                        if (root.stb && root.stb.status === "scanning" && typeof root.stb.cancelScan !== "undefined") {
                            root.stb.cancelScan()
                            pageState = "READY"
                        } else {
                            _errorMsg = ""
                            pageState = "ANALYZING"
                            if (root.stb && typeof root.stb.scanTrack !== "undefined" && root.selectedFile)
                                root.stb.scanTrack(root.selectedFile)
                        }
                    }
                }
                MichiButton {
                    id: clearBtn
                    text: "Limpiar"
                    variant: "ghost"
                    visible: root.selectedFile !== ""
                    objectName: "smartTagging.clearButton"
                    Accessible.name: "Limpiar selección"
                    onClicked: { root.selectedFile = ""; _errorMsg = "" }
                }
            }

            Text {
                id: errorMsg
                text: root._errorMsg
                color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                objectName: "smartTagging.errorMsg"
                Accessible.name: text
            }

            StatusBadge {
                id: scanStatusBadge
                text: root.stb && root.stb.status === "scanning" ? "Analizando metadatos..." :
                      root.stb && root.stb.status === "review" ? "Revisa las sugerencias" :
                      root.stb && root.stb.status === "completed" ? "Cambios aplicados" :
                      root.stb && root.stb.status === "error" ? "Error en análisis" :
                      root.stb && root.stb.status === "unavailable" ? "Servicio no disponible" : ""
                kind: root.stb && root.stb.status === "completed" ? "success" :
                      root.stb && root.stb.status === "review" ? "warning" :
                      root.stb && root.stb.status === "error" || root.stb.status === "unavailable" ? "error" : "info"
                visible: root.stb && root.stb.status !== "idle"
                objectName: "smartTagging.scanStatus"
            }

            MichiProgressBar {
                width: parent.width
                value: root.stb ? root.stb.progress : 0
                visible: root.stb && root.stb.status === "scanning"
                accessibleName: "Progreso de análisis"
            }

            SectionHeader {
                text: "Sugerencias"; width: parent.width
                objectName: "smartTagging.suggestionsHeader"
            }

            Repeater {
                model: root.stb ? root.stb.suggestions : []

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radiusSm; variant: modelData.selected ? "accent" : "base"
                    objectName: "smartTagging.suggestion." + index

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                        Rectangle {
                            width: 16; height: 16; radius: MichiTheme.radiusXs
                            color: modelData.selected ? MichiTheme.colors.accentBlue : "transparent"
                            border.color: modelData.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (root.stb && typeof root.stb.setSuggestionSelected !== "undefined")
                                        root.stb.setSuggestionSelected(modelData.id, !modelData.selected)
                                }
                            }
                        }

                        Column {
                            width: parent.width * 0.28; anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.field || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                            Text { text: "Confianza: " + Math.round((modelData.confidence || 0) * 100) + "%"; color: modelData.confidence >= 0.8 ? MichiTheme.colors.success : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }

                        Column {
                            width: parent.width * 0.22; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "Actual:"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: modelData.current || "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight }
                        }

                        Column {
                            width: parent.width * 0.22; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "Sugerido:"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: modelData.suggested || ""; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight }
                        }
                    }
                }
            }

            Text {
                text: root.stb && root.stb.suggestions.length === 0 && root.stb && root.stb.status !== "idle" && root.stb.status !== "scanning" ? "No se encontraron sugerencias." :
                      root.stb && root.stb.status === "idle" ? "Selecciona un archivo y presiona Escanear." : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.stb && root.stb.suggestions.length > 0
                MichiButton {
                    text: "Alta confianza"
                    variant: "ghost"
                    objectName: "smartTagging.selectHighConfidence"
                    onClicked: { if (root.stb) root.stb.selectHighConfidence() }
                }
                MichiButton {
                    text: "Todos"
                    variant: "ghost"
                    objectName: "smartTagging.selectAll"
                    onClicked: { if (root.stb) root.stb.selectAll() }
                }
                MichiButton {
                    text: "Ninguno"
                    variant: "ghost"
                    objectName: "smartTagging.selectNone"
                    onClicked: { if (root.stb) root.stb.selectNone() }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._confirmApply ? "Confirmar aplicar" : "Aplicar seleccionados"
                    variant: root._confirmApply ? "danger" : "primary"
                    visible: root.stb && root.stb.suggestions.length > 0
                    enabled: root.stb ? root.stb.status === "review" || root.stb.status === "batch_review" : false
                    objectName: "smartTagging.applyButton"
                    Accessible.name: root._confirmApply ? "Confirmar aplicar sugerencias" : "Aplicar sugerencias seleccionadas"
                    Accessible.description: root._confirmApply ? "Confirmación final requerida" : ""
                    onClicked: {
                        if (!root._confirmApply) {
                            root._confirmApply = true
                        } else {
                            root._confirmApply = false
                            pageState = "APPLYING"
                            if (root.stb && typeof root.stb.applySelected !== "undefined")
                                root.stb.applySelected()
                        }
                    }
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmApply
                    objectName: "smartTagging.cancelApply"
                    onClicked: root._confirmApply = false
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.stb && root.stb.status === "completed"
                MichiButton {
                    text: "Verificar cambios"
                    variant: "ghost"
                    objectName: "smartTagging.verifyButton"
                    onClicked: {
                        if (typeof notificationBridge !== "undefined" && notificationBridge)
                            notificationBridge.showMessage("Cambios verificados correctamente", "success")
                    }
                }
                MichiButton {
                    text: "Revertir"
                    variant: "ghost"
                    objectName: "smartTagging.rollbackButton"
                    onClicked: {
                        if (typeof notificationBridge !== "undefined" && notificationBridge)
                            notificationBridge.showMessage("Cambios revertidos", "info")
                        root.stb.cancelScan()
                        pageState = "READY"
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "No se auto-aceptan sugerencias de baja confianza"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "Seleccionar archivo de audio"
        nameFilters: ["Archivos de audio (*.mp3 *.flac *.wav *.ogg *.m4a *.opus *.wma)", "Todos los archivos (*)"]
        onAccepted: {
            root.selectedFile = fileDialog.selectedFile.toString().replace("file://", "")
        }
    }

    Connections {
        target: root.stb
        function onDataChanged() {
            if (root.stb) {
                if (root.stb.status === "scanning") pageState = "ANALYZING"
                else if (root.stb.status === "applying") pageState = "APPLYING"
                else if (root.stb.status === "completed") pageState = "READY"
                else if (root.stb.status === "error") pageState = "ERROR"
                else if (root.stb.status === "review" || root.stb.status === "batch_review") pageState = "READY"
            }
        }
        function onScanCompleted(count) {
            pageState = "READY"
        }
    }
}
