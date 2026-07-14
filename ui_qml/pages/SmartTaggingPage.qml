import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"
import "../components"
import "../materials"

Item {
    id: root
    objectName: "SmartTaggingPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Etiquetado inteligente"

    property var stb: typeof smartTaggingBridge !== "undefined" ? smartTaggingBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property string selectedFile: ""
    property string _errorMsg: ""
    property bool _confirmApply: false

    property list<string> _validFormats: ["mp3", "flac", "wav", "ogg", "m4a", "opus", "wma"]

    function isValidAudio(path) {
        if (root.stb && typeof root.stb.detectFormat === "function") {
            var ext = root.stb.detectFormat(path)
            return root._validFormats.indexOf(ext) >= 0
        }
        return false
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        objectName: "smartTaggingFlickable"
        Accessible.name: "Contenido de etiquetado inteligente"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Smart Tagging"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "smartTaggingTitle"
                Accessible.name: "Smart Tagging"
            }

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                objectName: "smartTaggingHero"
                Accessible.name: "Hero de etiquetado inteligente"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Etiquetado inteligente"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Sugerencias automáticas de metadatos para tu biblioteca."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: root.selectedFile ? "Archivo seleccionado" : (root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Canción desde Biblioteca" : "Analizar archivo")
                subtitle: root.selectedFile ? root.selectedFile.split("/").pop() : (root.sel && root.sel.hasSelection && root.sel.selectedTitle ? root.sel.selectedTitle : "Selecciona un archivo de audio")
                variant: root.selectedFile || (root.sel && root.sel.hasSelection) ? "accent" : "base"
                onClicked: fileDialog.open()
                objectName: "smartTaggingFileCard"
                Accessible.name: "Archivo seleccionado: " + (root.selectedFile || "ninguno")
            }

            Row {
                spacing: MichiTheme.spacing.sm
                objectName: "smartTaggingActionRow"
                Accessible.name: "Acciones de etiquetado"

                MichiButton {
                    text: root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Usar canción seleccionada" : "Seleccionar archivo"
                    variant: "primary"
                    objectName: "smartTaggingSelectButton"
                    Accessible.name: root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Usar canción seleccionada de biblioteca" : "Seleccionar archivo de audio"
                    activeFocusOnTab: true
                    KeyNavigation.tab: scanBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
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
                    text: root.stb && root.stb.status === "scanning" ? "Escaneando..." : "Escanear"
                    variant: "secondary"
                    enabled: root.selectedFile !== "" && (root.stb ? root.stb.status !== "scanning" : true)
                    objectName: "smartTaggingScanButton"
                    Accessible.name: root.selectedFile ? "Escanear archivo seleccionado" : "Selecciona un archivo primero"
                    Accessible.description: root.selectedFile ? "" : "Debes seleccionar un archivo de audio antes de escanear"
                    activeFocusOnTab: true
                    KeyNavigation.tab: clearBtn
                    KeyNavigation.backtab: root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? smartTaggingSelectButton : smartTaggingSelectButton
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (!root.isValidAudio(root.selectedFile)) {
                            root._errorMsg = "Formato no soportado. Usa MP3, FLAC, WAV, OGG, M4A, OPUS o WMA."
                            return
                        }
                        root._errorMsg = ""
                        if (root.stb && typeof root.stb.scanTrack !== "undefined" && root.selectedFile)
                            root.stb.scanTrack(root.selectedFile)
                    }
                }

                MichiButton {
                    id: clearBtn
                    text: "Limpiar"
                    variant: "ghost"
                    visible: root.selectedFile !== ""
                    objectName: "smartTaggingClearButton"
                    Accessible.name: "Limpiar selección"
                    activeFocusOnTab: true
                    KeyNavigation.tab: root._errorMsg !== "" ? errorMsg : (root.stb && root.stb.status !== "idle" ? statusBadge : suggestionSection)
                    KeyNavigation.backtab: scanBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { root.selectedFile = ""; root._errorMsg = "" }
                }
            }

            Text {
                id: errorMsg
                text: root._errorMsg
                color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                objectName: "smartTaggingError"
                Accessible.name: "Error: " + root._errorMsg
                Accessible.role: Accessible.Alert
            }

            StatusBadge {
                id: statusBadge
                text: root.stb && root.stb.status === "scanning" ? "Escaneando..." :
                      root.stb && root.stb.status === "done" ? "Análisis completado" :
                      root.stb && root.stb.status === "error" ? "Error en escaneo" :
                      root.stb && root.stb.status === "unavailable" ? "Servicio no disponible" : ""
                kind: root.stb && root.stb.status === "done" ? "success" :
                      root.stb && (root.stb.status === "error" || root.stb.status === "unavailable") ? "error" : "info"
                visible: root.stb && root.stb.status !== "idle"
                objectName: "smartTaggingStatusBadge"
                Accessible.name: "Estado: " + text
            }

            SectionHeader {
                id: suggestionSection
                text: "Sugerencias"; width: parent.width
                objectName: "smartTaggingSuggestionsHeader"
                Accessible.name: "Sugerencias de etiquetado"
            }

            Repeater {
                model: root.stb ? root.stb.suggestions : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: "base"
                    objectName: "smartTaggingSuggestion_" + index
                    Accessible.name: modelData.field + ": " + (modelData.current || "vacío") + " → " + (modelData.suggested || "—")
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text {
                            width: parent.width * 0.25; text: modelData.field || ""
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30; text: modelData.current || "—"
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30; text: "→ " + (modelData.suggested || "")
                            color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Text {
                text: "No hay sugerencias. Escanea un archivo para comenzar."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: root.stb && root.stb.suggestions.length === 0
                objectName: "smartTaggingEmptyState"
                Accessible.name: "No hay sugerencias"
            }

            Row {
                spacing: MichiTheme.spacing.sm
                objectName: "smartTaggingApplyRow"
                Accessible.name: "Confirmación de aplicación"

                MichiButton {
                    text: root._confirmApply ? "Confirmar aplicar sugerencias" : "Aplicar sugerencias"
                    variant: root._confirmApply ? "danger" : "primary"
                    visible: root.stb && root.stb.suggestions.length > 0
                    objectName: "smartTaggingApplyButton"
                    Accessible.name: root._confirmApply ? "Confirmar aplicar todas las sugerencias" : "Aplicar sugerencias"
                    Accessible.description: root._confirmApply ? "Esta acción modificará los metadatos del archivo" : ""
                    activeFocusOnTab: true
                    KeyNavigation.tab: cancelApplyBtn
                    KeyNavigation.backtab: clearBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (!root._confirmApply) {
                            root._confirmApply = true
                        } else {
                            root._confirmApply = false
                            if (typeof notificationBridge !== "undefined" && notificationBridge)
                                notificationBridge.showMessage("Sugerencias aplicadas (simulado)", "success")
                        }
                    }
                }

                MichiButton {
                    id: cancelApplyBtn
                    text: "Cancelar"
                    variant: "ghost"
                    visible: root._confirmApply
                    objectName: "smartTaggingCancelApplyButton"
                    Accessible.name: "Cancelar aplicación de sugerencias"
                    activeFocusOnTab: true
                    KeyNavigation.backtab: smartTaggingApplyButton
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._confirmApply = false
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                objectName: "smartTaggingInfoPanel"
                Accessible.name: "Información de interfaz"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
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
}
