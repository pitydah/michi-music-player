import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "syncHistoryPlaceholderPage"
    // Compatibility with the current route registry and placeholder smoke test.
    property string featureState: "planned"
    property var devices: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property string filterText: ""
    property string feedback: ""
    property bool feedbackError: false

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Historial de sincronización")

    function refreshHistory() {
        if (!root.devices) return
        root.devices.refresh()
        var result = root.devices.history("")
        root.feedbackError = !result || !result.ok
        root.feedback = root.feedbackError
                ? qsTr("No se pudo cargar el historial: ") + (result && result.error ? result.error : qsTr("error desconocido"))
                : qsTr("Historial actualizado")
    }

    function matches(item) {
        if (!root.filterText) return true
        var query = root.filterText.toLowerCase()
        var text = String(item.file_name || item.source_path || item.device || item.destination_path || item.status || "").toLowerCase()
        return text.indexOf(query) >= 0
    }

    function humanBytes(value) {
        var bytes = Number(value || 0)
        if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(2) + " GB"
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB"
        if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB"
        return bytes + " B"
    }

    Component.onCompleted: root.refreshHistory()

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
                height: 140
                radius: MichiTheme.radius.lg
                showGlow: true
                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm
                    Text {
                        text: qsTr("Historial de sincronización")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        width: parent.width * 0.8
                        wrapMode: Text.WordWrap
                        text: qsTr("Consulta transferencias, reintenta fallos y cancela trabajos todavía activos.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            RowLayout {
                width: parent.width
                MichiSearchField {
                    Layout.fillWidth: true
                    placeholderText: qsTr("Buscar por archivo, dispositivo, destino o estado")
                    onSearchTextChanged: root.filterText = text
                }
                MichiButton {
                    text: qsTr("Actualizar")
                    variant: "secondary"
                    onClicked: root.refreshHistory()
                }
                MichiButton {
                    text: qsTr("Limpiar historial")
                    variant: "danger"
                    enabled: root.devices && root.devices.transferHistory.length > 0
                    onClicked: clearDialog.open()
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

            SectionHeader {
                width: parent.width
                text: qsTr("Trabajos activos")
            }

            Text {
                visible: !root.devices || root.devices.transferJobs.length === 0
                color: MichiTheme.colors.textMuted
                text: qsTr("No hay trabajos en curso.")
            }

            Repeater {
                model: root.devices ? root.devices.transferJobs : []
                delegate: GlassMaterial {
                    width: contentColumn.width
                    height: 92
                    radius: MichiTheme.radius.md
                    variant: "base"
                    visible: root.matches(modelData)

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text {
                                text: modelData.file_name || qsTr("Transferencia")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightSemiBold
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                            Text {
                                text: (modelData.status || modelData.state || qsTr("desconocido"))
                                      + " · " + root.humanBytes(modelData.transferred_bytes)
                                      + " / " + root.humanBytes(modelData.total_bytes)
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                            }
                        }
                        MichiButton {
                            text: qsTr("Cancelar")
                            variant: "danger"
                            enabled: ["queued", "transferring", "cancel_requested"].indexOf(String(modelData.state || modelData.status).toLowerCase()) >= 0
                            onClicked: {
                                var result = root.devices.cancelTransfer(modelData.job_id || "")
                                root.feedbackError = !result || !result.ok
                                root.feedback = root.feedbackError ? qsTr("No se pudo cancelar") : qsTr("Cancelación solicitada")
                            }
                        }
                        MichiButton {
                            text: qsTr("Reintentar")
                            variant: "secondary"
                            enabled: ["failed", "cancelled", "error"].indexOf(String(modelData.state || modelData.status).toLowerCase()) >= 0
                            onClicked: {
                                var result = root.devices.retryTransfer(modelData.job_id || "")
                                root.feedbackError = !result || !result.ok
                                root.feedback = root.feedbackError ? qsTr("No se pudo reintentar") : qsTr("Transferencia reintentada")
                            }
                        }
                    }
                }
            }

            SectionHeader {
                width: parent.width
                text: qsTr("Operaciones finalizadas")
            }

            Text {
                visible: !root.devices || root.devices.transferHistory.length === 0
                width: parent.width
                wrapMode: Text.WordWrap
                color: MichiTheme.colors.textMuted
                text: qsTr("Todavía no existen operaciones registradas.")
            }

            Repeater {
                model: root.devices ? root.devices.transferHistory : []
                delegate: GlassMaterial {
                    width: contentColumn.width
                    height: visible ? 82 : 0
                    radius: MichiTheme.radius.md
                    variant: "base"
                    visible: root.matches(modelData)

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                                text: modelData.file_name || modelData.source_path || modelData.title || qsTr("Sincronización")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                                text: modelData.destination_path || modelData.device || ""
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                            }
                        }
                        StatusBadge {
                            text: modelData.status || modelData.state || qsTr("completado")
                            kind: ["completed", "success", "done"].indexOf(String(modelData.status || modelData.state).toLowerCase()) >= 0 ? "success" : "warning"
                        }
                        Text {
                            text: modelData.completed_at || modelData.finished_at || modelData.created_at || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }
                    }
                }
            }
        }
    }

    ConfirmActionDialog {
        id: clearDialog
        title: qsTr("Limpiar historial")
        message: qsTr("Se eliminará el registro local de sincronizaciones. Los archivos transferidos no serán borrados del dispositivo.")
        onConfirmed: {
            var result = root.devices ? root.devices.clearTransferHistory() : { ok: false, error: "BRIDGE_UNAVAILABLE" }
            root.feedbackError = !result || !result.ok
            root.feedback = root.feedbackError ? qsTr("No se pudo limpiar el historial") : qsTr("Historial limpiado")
        }
    }
}
