import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Smart Tagging Workflow"
    objectName: "smartTaggingWorkflowPage"
    focus: true
    id: root

    property var stb: typeof smartTaggingBridge !== "undefined" ? smartTaggingBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string _selectedFile: ""
    property bool _confirmApply: false

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
                text: "Smart Tagging"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 100; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text { text: "Etiquetado inteligente"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                    Text { text: "Analiza, sugiere y aplica metadatos con control total."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: root._selectedFile ? "Archivo seleccionado" : "Seleccionar archivo"
                subtitle: root._selectedFile ? root._selectedFile.split("/").pop() : "Elige un archivo de audio"
                variant: root._selectedFile ? "accent" : "base"
                onClicked: fileDialog.open()
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Analizar"
                    variant: "primary"
                    enabled: root._selectedFile !== "" && (root.stb ? root.stb.status !== "scanning" : true)
                    onClicked: {
                        if (root.stb && typeof root.stb.scanTrack !== "undefined" && root._selectedFile)
                            root.stb.scanTrack(root._selectedFile)
                    }
                }
                MichiButton {
                    text: root.stb && root.stb.status === "scanning" ? "Cancelar" : "Limpiar"
                    variant: "ghost"
                    onClicked: {
                        if (root.stb && root.stb.status === "scanning" && typeof root.stb.cancelScan !== "undefined")
                            root.stb.cancelScan()
                        else
                            root._selectedFile = ""
                    }
                }
            }

            StatusBadge {
                text: root.stb && root.stb.status === "scanning" ? "Analizando..." :
                      root.stb && root.stb.status === "review" ? "Revisa las sugerencias" :
                      root.stb && root.stb.status === "completed" ? "Cambios aplicados" :
                      root.stb && root.stb.status === "error" ? "Error en análisis" : ""
                kind: root.stb && root.stb.status === "completed" ? "success" :
                      root.stb && root.stb.status === "error" ? "error" :
                      root.stb && root.stb.status === "review" ? "warning" : "info"
                visible: root.stb && root.stb.status !== "idle"
            }

            MichiProgressBar {
                width: parent.width
                value: root.stb ? root.stb.progress : 0
                visible: root.stb && root.stb.status === "scanning"
            }

            SectionHeader { text: "Sugerencias"; width: parent.width }

            Repeater {
                model: root.stb ? root.stb.suggestions : []

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radiusSm; variant: modelData.selected ? "accent" : "base"

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                        Rectangle {
                            width: 16; height: 16; radius: 2
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
                            width: parent.width * 0.30; anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.field || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                            Text { text: "Confianza: " + Math.round((modelData.confidence || 0) * 100) + "%"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }

                        Column {
                            width: parent.width * 0.25; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "Actual:"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: modelData.current || "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight }
                        }

                        Column {
                            width: parent.width * 0.25; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "Sugerido:"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: modelData.suggested || ""; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight }
                        }
                    }
                }
            }

            Text {
                text: root.stb && root.stb.suggestions.length === 0 && root.stb && root.stb.status !== "idle" ? "No se encontraron sugerencias." :
                      root.stb && root.stb.status === "idle" ? "Selecciona un archivo y presiona Analizar." : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.stb && root.stb.suggestions.length > 0
                MichiButton {
                    text: "Seleccionar alta confianza"
                    variant: "ghost"
                    onClicked: { if (root.stb) root.stb.selectHighConfidence() }
                }
                MichiButton {
                    text: "Seleccionar todos"
                    variant: "ghost"
                    onClicked: { if (root.stb) root.stb.selectAll() }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._confirmApply ? "Confirmar aplicar" : "Aplicar seleccionados"
                    variant: root._confirmApply ? "danger" : "primary"
                    visible: root.stb && root.stb.suggestions.length > 0
                    enabled: root.stb ? root.stb.status === "review" || root.stb.status === "batch_review" : false
                    onClicked: {
                        if (!root._confirmApply) {
                            root._confirmApply = true
                        } else {
                            root._confirmApply = false
                            if (root.stb && typeof root.stb.applySelected !== "undefined")
                                root.stb.applySelected()
                        }
                    }
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmApply
                    onClicked: root._confirmApply = false
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
            root._selectedFile = fileDialog.selectedFile.toString().replace("file://", "")
        }
    }
}
