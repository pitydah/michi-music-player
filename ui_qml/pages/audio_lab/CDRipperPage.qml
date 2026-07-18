import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../components/audio_lab"

/**
 * Página de Ripeo de CD - Extrae pistas de CDs de audio
 * Usa CDRipperService desde el bridge
 */
Page {
    id: page

    header: SectionHeader {
        text: "Ripeo de CD"
        // onBackClicked eliminado
    }

    property var cdDevices: []
    property var currentCDInfo: null
    property string selectedDevice: ""
    property bool isLoading: false
    property bool isRipping: false
    property var tracksToRip: []
    property string outputFolder: "/home/user/Music/CD Rips"
    property string availableSpace: "—"
    property real perTrackSizeMB: 0

    Component.onCompleted: {
        loadCDDevices()
    }

    function loadCDDevices() {
        isLoading = true
        cdDevices = audioLabBridge.detectCDDrives()
        isLoading = false
        
        if (cdDevices.length === 0) {
            statusMessage.text = "No se detectaron unidades de CD. Conecta una unidad e inserta un CD."
        } else if (cdDevices.length === 1) {
            selectedDevice = cdDevices[0].device
            loadCDInfo(selectedDevice)
        }
    }

    function loadCDInfo(device) {
        isLoading = true
        currentCDInfo = audioLabBridge.getCDInfo(device)
        isLoading = false
        refreshSpaceInfo()
        
        if (currentCDInfo && currentCDInfo.ok) {
            statusMessage.text = `CD detectado: ${currentCDInfo.album_title || "Desconocido"}`
            tracksToRip = currentCDInfo.tracks.map(function(t) { return {track_number: t.track_number, title: t.title, artist: t.artist, duration: t.duration, selected: true} })
        } else {
            statusMessage.text = "No se pudo leer el CD o no hay uno insertado."
        }
    }

    function ripSelectedTracks() {
        if (!selectedDevice || !currentCDInfo) return
        
        isRipping = true
        const selectedTracks = tracksToRip.filter(t => t.selected)
        
        previewDialog.previewData = selectedTracks.map(t => ({
            original: `Pista ${t.track_number} (${t.title})`,
            result: `${outputFolder}/${t.track_number.toString().padStart(2, '0')}-${t.title}.${formatSelector.currentText.toLowerCase()}`,
            size: perTrackSizeMB > 0 ? `~${perTrackSizeMB.toFixed(0)} MB` : "—"
        }))
        
        previewDialog.spaceSufficient = true
        previewDialog.requiredSpace = perTrackSizeMB > 0 ? `~${(selectedTracks.length * perTrackSizeMB).toFixed(0)} MB` : "—"
        previewDialog.availableSpace = availableSpace
        previewDialog.open()
    }

    function confirmRip() {
        const selectedTracks = tracksToRip.filter(t => t.selected)
        const format = formatSelector.currentText.toLowerCase()
        let trackIndex = 0
        
        function ripNext() {
            if (trackIndex >= selectedTracks.length) {
                isRipping = false
                notificationBridge.showSuccess("Ripeo completado")
                return
            }
            
            const track = selectedTracks[trackIndex]
            const outputPath = `${outputFolder}/${track.track_number.toString().padStart(2, '0')}-${track.title}.${format}`
            
            statusMessage.text = `Extrayendo pista ${track.track_number}/${selectedTracks.length}...`
            
            const result = audioLabBridge.ripCDTrack(
                selectedDevice,
                track.track_number,
                outputPath,
                format
            )
            
            if (!result.ok) {
                notificationBridge.showError(`Error en pista ${track.track_number}: ${result.error}`)
            }
            
            trackIndex++
            Qt.callLater(ripNext)
        }
        
        ripNext()
    }

    function refreshSpaceInfo() {
        var info = audioLabBridge.getSpaceInfo ? audioLabBridge.getSpaceInfo() : null
        if (info && info.ok) {
            availableSpace = info.available
            perTrackSizeMB = info.perTrackMB || 30
        } else {
            availableSpace = "—"
            perTrackSizeMB = 0
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: container.width
        clip: true

        ColumnLayout {
            id: container
            width: Math.max(parent.width, 800)
            anchors.margins: 20
            spacing: 20

            // Selector de dispositivo
            GlassCard {
                Layout.fillWidth: true
                anchors.margins: 15

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Label {
                        text: "Unidad de CD"
                        font.bold: true
                        font.pixelSize: 14
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: cdDevices.map(d => d.model || d.device)
                        currentIndex: cdDevices.findIndex(d => d.device === selectedDevice)
                        
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && cdDevices.length > 0) {
                                selectedDevice = cdDevices[currentIndex].device
                                loadCDInfo(selectedDevice)
                            }
                        }
                    }

                    Label {
                        visible: cdDevices.length === 0
                        text: "⚠️ No se detectaron unidades de CD"
                        color: MichiTheme.warning
                        font.pixelSize: 12
                    }
                }
            }

            // Información del CD
            GlassCard {
                Layout.fillWidth: true
                anchors.margins: 15
                visible: currentCDInfo && currentCDInfo.ok

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Label {
                        text: currentCDInfo ? currentCDInfo.album_title : ""
                        font.bold: true
                        font.pixelSize: 18
                    }

                    RowLayout {
                        Label {
                            text: currentCDInfo ? `Artista: ${currentCDInfo.album_artist || "Varios"}` : ""
                            color: MichiTheme.textSecondary
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: currentCDInfo ? `${currentCDInfo.total_tracks} pistas` : ""
                            color: MichiTheme.textSecondary
                        }
                    }
                }
            }

            // Lista de pistas
            GlassCard {
                Layout.fillWidth: true
                anchors.margins: 15
                visible: currentCDInfo && currentCDInfo.ok

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15

                    RowLayout {
                        Label {
                            text: "Seleccionar pistas"
                            font.bold: true
                            font.pixelSize: 14
                        }
                        Item { Layout.fillWidth: true }
                        CheckBox {
                            text: "Todas"
                            checked: tracksToRip.every(t => t.selected)
                            onToggled: {
                                tracksToRip.forEach(t => t.selected = checked)
                            }
                        }
                    }

                    Repeater {
                        model: tracksToRip

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            CheckBox {
                                checked: modelData.selected
                                onToggled: modelData.selected = checked
                            }

                            Label {
                                text: `${modelData.track_number}. ${modelData.title}`
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Label {
                                text: modelData.duration > 0 ? 
                                      `${Math.floor(modelData.duration / 60)}:${(modelData.duration % 60).toString().padStart(2, '0')}` : 
                                      "--:--"
                                color: MichiTheme.textSecondary
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }

            // Configuración de salida
            GlassCard {
                Layout.fillWidth: true
                anchors.margins: 15

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15

                    Label {
                        text: "Configuración"
                        font.bold: true
                        font.pixelSize: 14
                    }

                    // Formato
                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "Formato:"
                            width: 100
                        }

                        ComboBox {
                            id: formatSelector
                            Layout.fillWidth: true
                            model: ["FLAC", "WAV", "MP3", "AAC"]
                            currentIndex: 0
                        }
                    }

                    // Carpeta de salida
                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "Guardar en:"
                            width: 100
                        }

                        TextField {
                            id: outputFolderField
                            Layout.fillWidth: true
                            text: outputFolder
                            placeholderText: "Carpeta de destino"
                            onTextChanged: outputFolder = text
                        }

                        Button {
                            text: "..."
                            onClicked: folderDialog.open()
                        }
                    }

                    // Modo seguro
                    CheckBox {
                        text: "Modo seguro (relectura automática de errores)"
                        checked: true
                    }
                }
            }

            // Botón de acción
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                text: isRipping ? "Extrayendo..." : "Extraer Pistas Seleccionadas"
                enabled: selectedDevice && tracksToRip.some(t => t.selected) && !isRipping
                highlighted: true

                onClicked: ripSelectedTracks()
            }

            // Mensaje de estado
            Label {
                id: statusMessage
                Layout.fillWidth: true
                text: "Selecciona una unidad de CD para comenzar"
                color: MichiTheme.textSecondary
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 12
            }
        }
    }

    // Diálogo de confirmación
    AudioLabPreviewDialog {
        id: previewDialog
        onConfirmed: confirmRip()
    }

    // Selector de carpeta
    FolderDialog {
        id: folderDialog
        currentFolder: StandardPaths.standardLocations(StandardPaths.MusicLocation)[0]
        onAccepted: {
            outputFolder = selectedFolder
            outputFolderField.text = selectedFolder
        }
    }

    // Overlay de carga
    LoadingState {
        visible: isLoading
        anchors.fill: parent
        message: isLoading ? "Leyendo CD..." : ""
    }
}
