import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "portablePlayersPlaceholderPage"
    // Temporary compatibility with route metadata and its legacy smoke test.
    property string featureState: "planned"
    property var devices: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property string selectedDeviceKey: ""
    property string selectedDeviceName: ""
    property string sourceFile: ""
    property string destinationFolder: ""
    property string feedback: ""
    property bool feedbackError: false

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Reproductores portátiles")

    function deviceKey(device) {
        if (!device) return ""
        return device.key || ((device.protocol || device.device || "unknown") + ":" + (device.serial || device.alias || ""))
    }

    function showResult(result, successText) {
        root.feedbackError = !result || !result.ok
        root.feedback = root.feedbackError
                ? qsTr("No se pudo completar la operación: ") + (result && (result.message || result.error) ? (result.message || result.error) : qsTr("error desconocido"))
                : successText
    }

    function refreshDevices() {
        if (!root.devices) return
        root.showResult(root.devices.discover(), qsTr("Búsqueda de dispositivos completada"))
        root.devices.refresh()
    }

    function startTransfer() {
        if (!root.devices || !root.sourceFile || !root.destinationFolder) return
        var validation = root.devices.validateAudioFile(root.sourceFile)
        if (!validation || !validation.ok) {
            root.showResult(validation, "")
            return
        }
        var separator = root.destinationFolder.endsWith("/") ? "" : "/"
        var destination = root.destinationFolder + separator + root.devices.fileName(root.sourceFile)
        root.showResult(root.devices.startTransfer(root.sourceFile, destination), qsTr("Transferencia iniciada"))
    }

    Component.onCompleted: {
        if (root.devices) {
            root.devices.refresh()
            root.refreshDevices()
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 150
                radius: MichiTheme.radius.lg
                showGlow: true
                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm
                    Text {
                        text: qsTr("Reproductores portátiles")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        width: parent.width * 0.78
                        wrapMode: Text.WordWrap
                        text: qsTr("Detecta DAPs mediante almacenamiento USB o MTP y transfiere exclusivamente archivos de audio.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            MichiBanner {
                width: parent.width
                message: qsTr("Michi Sync Suite no copia video. Los dispositivos vendidos como ‘MP4’ se usan únicamente como destinos de audio.")
                kind: "info"
                dismissible: false
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("Buscar dispositivos")
                    variant: "primary"
                    enabled: root.devices !== null
                    onClicked: root.refreshDevices()
                }
                StatusBadge {
                    text: root.devices ? root.devices.pageState : qsTr("Bridge no disponible")
                    kind: root.devices && root.devices.pageState === "FAILED" ? "error" : "info"
                }
            }

            MichiBanner {
                width: parent.width
                visible: root.feedback !== ""
                message: root.feedback
                kind: root.feedbackError ? "error" : "success"
                dismissible: true
                onDismissed: root.feedback = ""
            }

            SectionHeader { width: parent.width; text: qsTr("Dispositivos detectados") }

            Text {
                visible: !root.devices || root.devices.discovered.length === 0
                width: parent.width
                wrapMode: Text.WordWrap
                color: MichiTheme.colors.textMuted
                text: qsTr("No se detectaron reproductores. Conecta el dispositivo, habilita MTP o monta su almacenamiento USB y vuelve a buscar.")
            }

            Repeater {
                model: root.devices ? root.devices.discovered : []
                delegate: GlassMaterial {
                    width: contentColumn.width
                    height: 88
                    radius: MichiTheme.radius.md
                    variant: root.selectedDeviceKey === root.deviceKey(modelData) ? "accent" : "base"
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text {
                                text: modelData.alias || modelData.name || qsTr("Reproductor portátil")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }
                            Text {
                                text: String(modelData.protocol || modelData.device || qsTr("desconocido")).toUpperCase()
                                      + (modelData.serial ? " · " + modelData.serial : "")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                            }
                        }
                        MichiButton {
                            text: qsTr("Seleccionar")
                            variant: "secondary"
                            onClicked: {
                                root.selectedDeviceKey = root.deviceKey(modelData)
                                root.selectedDeviceName = modelData.alias || modelData.name || root.selectedDeviceKey
                            }
                        }
                        MichiButton {
                            text: qsTr("Emparejar")
                            variant: "primary"
                            onClicked: root.showResult(root.devices.pairDevice(root.deviceKey(modelData)), qsTr("Dispositivo emparejado"))
                        }
                    }
                }
            }

            SectionHeader { width: parent.width; text: qsTr("Transferencia manual") }

            GlassMaterial {
                width: parent.width
                height: 190
                radius: MichiTheme.radius.md
                variant: "base"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md
                    spacing: MichiTheme.spacing.sm
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            text: root.sourceFile
                            placeholderText: qsTr("Archivo de audio de origen")
                        }
                        MichiButton { text: qsTr("Elegir archivo"); variant: "secondary"; onClicked: sourceDialog.open() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            text: root.destinationFolder
                            placeholderText: qsTr("Carpeta Music del dispositivo")
                        }
                        MichiButton { text: qsTr("Elegir destino"); variant: "secondary"; onClicked: destinationDialog.open() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            Layout.fillWidth: true
                            color: MichiTheme.colors.textSecondary
                            text: root.selectedDeviceName ? qsTr("Seleccionado: ") + root.selectedDeviceName : qsTr("Selecciona cualquier almacenamiento montado como destino.")
                            elide: Text.ElideRight
                        }
                        MichiButton {
                            text: qsTr("Transferir audio")
                            variant: "primary"
                            enabled: root.devices && root.sourceFile !== "" && root.destinationFolder !== ""
                            onClicked: root.startTransfer()
                        }
                    }
                }
            }

            SectionHeader { width: parent.width; text: qsTr("Trabajos activos") }
            Text {
                visible: !root.devices || root.devices.transferJobs.length === 0
                color: MichiTheme.colors.textMuted
                text: qsTr("No hay transferencias activas.")
            }
            Repeater {
                model: root.devices ? root.devices.transferJobs : []
                delegate: GlassCard {
                    width: contentColumn.width
                    height: 76
                    title: modelData.file_name || qsTr("Transferencia")
                    subtitle: (modelData.status || modelData.state || "") + " · "
                              + Math.round((modelData.transferred_bytes || 0) / 1048576) + " / "
                              + Math.round((modelData.total_bytes || 0) / 1048576) + " MB"
                    variant: "base"
                }
            }
        }
    }

    FileDialog {
        id: sourceDialog
        title: qsTr("Seleccionar archivo de audio")
        nameFilters: [qsTr("Audio (*.mp3 *.flac *.wav *.ogg *.opus *.m4a *.aac *.wma *.dsf *.dff *.ape *.aiff *.alac)")]
        onAccepted: root.sourceFile = selectedFile.toLocalFile()
    }

    FolderDialog {
        id: destinationDialog
        title: qsTr("Seleccionar carpeta de destino")
        onAccepted: root.destinationFolder = selectedFolder.toLocalFile()
    }
}
