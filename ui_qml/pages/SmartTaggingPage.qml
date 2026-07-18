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

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: qsTr("Smart Tagging")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radius.lg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: qsTr("Etiquetado inteligente")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: qsTr("Sugerencias automáticas de metadatos para tu biblioteca.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: root.selectedFile ? "Archivo seleccionado" : (root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Canción desde Biblioteca" : qsTr("Analizar archivo"))
                subtitle: root.selectedFile ? root.selectedFile.split("/").pop() : (root.sel && root.sel.hasSelection && root.sel.selectedTitle ? root.sel.selectedTitle : qsTr("Selecciona un archivo de audio"))
                variant: root.selectedFile || (root.sel && root.sel.hasSelection) ? "accent" : "base"
                onClicked: fileDialog.open()
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    objectName: "selectFileButton"
                    text: root.sel && root.sel.hasSelection && root.sel.selectedSource === "track_id" ? "Usar canción seleccionada" : qsTr("Seleccionar archivo")
                    variant: "primary"
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
                    objectName: "scanFileButton"
                    text: root.stb && root.stb.status === "scanning" ? "Escaneando..." : qsTr("Escanear")
                    variant: "secondary"
                    enabled: root.selectedFile !== "" && (root.stb ? root.stb.status !== "scanning" : true)
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
                    objectName: "clearFileButton"
                    text: qsTr("Limpiar")
                    variant: "ghost"
                    visible: root.selectedFile !== ""
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
            }

            SectionHeader {
                id: suggestionSection
                text: qsTr("Sugerencias"); width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.stb && root.stb.suggestions.length > 0

                MichiButton {
                    text: qsTr("Seleccionar todas")
                    variant: "secondary"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stb && typeof root.stb.selectAll === "function")
                            root.stb.selectAll()
                    }
                }

                MichiButton {
                    text: qsTr("Seleccionar por confianza")
                    variant: "secondary"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stb && typeof root.stb.selectHighConfidence === "function")
                            root.stb.selectHighConfidence()
                    }
                }
            }

            Repeater {
                model: root.stb ? root.stb.suggestions : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radius.sm; variant: "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        CheckBox {
                            id: sugCheck
                            anchors.verticalCenter: parent.verticalCenter
                            checked: modelData.selected || false
                            onCheckedChanged: {
                                if (root.stb && typeof root.stb.setSuggestionSelected === "function")
                                    root.stb.setSuggestionSelected(modelData.id, checked)
                            }
                        }
                        Text {
                            width: parent.width * 0.22; text: modelData.field || ""
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.25; text: modelData.current || "—"
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.25; text: qsTr("→ ") + (modelData.suggested || "")
                            color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Text {
                text: qsTr("No hay sugerencias. Escanea un archivo para comenzar.")
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: root.stb && root.stb.suggestions.length === 0
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    objectName: "applySuggestionsButton"
                    text: root._confirmApply ? "Confirmar aplicar sugerencias" : qsTr("Aplicar sugerencias")
                    variant: root._confirmApply ? "danger" : "primary"
                    visible: root.stb && root.stb.suggestions.length > 0
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
                            if (root.stb && typeof root.stb.applySelected === "function") {
                                var result = root.stb.applySelected()
                                if (typeof notificationBridge !== "undefined" && notificationBridge) {
                                    if (result && result.ok) {
                                        notificationBridge.showMessage("Sugerencias aplicadas correctamente", "success")
                                    } else {
                                        notificationBridge.showMessage("Error al aplicar sugerencias: " + (result && result.error ? result.error : "desconocido"), "error")
                                    }
                                }
                            }
                        }
                    }
                }

                MichiButton {
                    id: cancelApplyBtn
                    objectName: "cancelApplyButton"
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    visible: root._confirmApply
                    activeFocusOnTab: true
                    KeyNavigation.backtab: smartTaggingApplyButton
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._confirmApply = false
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: qsTr("Interfaz clásica disponible"); kind: "info" }
                    StatusBadge { text: qsTr("Experimental"); kind: "experimental" }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: qsTr("Seleccionar archivo de audio")
        nameFilters: ["Archivos de audio (*.mp3 *.flac *.wav *.ogg *.m4a *.opus *.wma)", "Todos los archivos (*)"]
        onAccepted: {
            root.selectedFile = fileDialog.selectedFile.toString().replace("file://", "")
        }
    }
}
