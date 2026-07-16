import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Sync History"
    objectName: "deviceSyncHistory"
    focus: true
    id: root

    property string deviceKey: ""
    property var historyEntries: []

    signal clearHistoryClicked()

    implicitHeight: childrenRect.height

    objectName: "DeviceSyncHistory"
    Accessible.role: Accessible.Pane
    Accessible.name: "Historial de sincronización"

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Historial de sincronización"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    width: parent.width - 100
                    objectName: "syncHistoryTitle"
                    Accessible.name: "Historial de sincronización"
                }

                MichiButton {
                    text: "Limpiar"
                    variant: "ghost"
                    onClicked: root.clearHistoryClicked()
                    objectName: "clearHistoryButton"
                    Accessible.name: "Limpiar historial de sincronización"
                }
            }

            Repeater {
                model: root.historyEntries

                Rectangle {
                    width: parent.width
                    height: 56
                    color: index % 2 === 0 ? MichiTheme.colors.surface : "transparent"
                    radius: MichiTheme.radiusSm
                    objectName: "syncHistoryRow_" + index
                    Accessible.name: modelData.job_id || "Entrada de historial"

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Column {
                            width: parent.width - 120
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: modelData.job_id || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                                width: parent.width
                                objectName: "syncHistoryJobId_" + index
                            }

                            Text {
                                text: modelData.timestamp ? new Date(modelData.timestamp * 1000).toLocaleString() : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }

                        Column {
                            spacing: MichiTheme.spacing.xs
                            anchors.verticalCenter: parent.verticalCenter

                            StatusBadge {
                                text: {
                                    switch (modelData.status) {
                                        case "completed": return "Completado"
                                        case "failed": return "Falló"
                                        case "cancelled": return "Cancelado"
                                        default: return modelData.status || "Desconocido"
                                    }
                                }
                                kind: {
                                    switch (modelData.status) {
                                        case "completed": return "success"
                                        case "failed": return "error"
                                        case "cancelled": return "disconnected"
                                        default: return "info"
                                    }
                                }
                                objectName: "syncHistoryStatus_" + index
                                Accessible.name: text
                            }

                            Text {
                                text: modelData.direction === "to_device" ? "→ Dispositivo" : "← Dispositivo"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }
                    }
                }
            }

            Text {
                text: root.historyEntries.length === 0 ? "No hay actividad de sincronización." : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.historyEntries.length === 0
                objectName: "syncHistoryEmptyMessage"
                Accessible.name: "No hay actividad de sincronización"
            }
        }
    }
}
