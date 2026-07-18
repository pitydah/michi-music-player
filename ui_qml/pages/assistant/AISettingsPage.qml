import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "AI Settings"
    objectName: "aiSettingsPage"
    focus: true
    id: root

    property var ai: typeof michiAiBridge !== "undefined" ? michiAiBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property string _selectedBackend: root.ai ? root.ai.backendType : "calico"
    property real _downloadProgress: root.ai ? root.ai.downloadProgress : 0

    function goBack() {
        if (root.nav) root.nav.back()
    }

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

            SectionHeader { text: "Asistente Michi AI"; width: parent.width }

            Text {
                width: parent.width
                text: "Selecciona el backend del asistente. Michi Calico está siempre disponible sin descargas adicionales."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: [
                    {id: "calico", name: "Michi Calico 🐱", desc: "Siempre disponible. Sin descarga. Reglas + plantillas en español.", size: "0 MB", ram: "< 50 MB", cpu: "Cualquiera", status: "always"},
                    {id: "munchkin", name: "Michi Munchkin 🐈", desc: "Pequeño y rápido. Para PCs básicos.", size: "350 MB", ram: "~500 MB", cpu: "2 núcleos", status: ""},
                    {id: "carey", name: "Michi Carey 🐈‍⬛", desc: "Equilibrado. Para PCs de gama media.", size: "1 GB", ram: "~1.5 GB", cpu: "4 núcleos", status: ""},
                    {id: "maine_coon", name: "Michi Maine Coon 🐱‍👓", desc: "El más capaz. Para PCs potentes.", size: "2 GB", ram: "~3 GB", cpu: "6+ núcleos", status: ""},
                    {id: "sphynx", name: "Michi Sphynx 🐱‍💻", desc: "Usa Ollama (modelo externo).", size: "Variable", ram: "Variable", cpu: "Variable", status: ""},
                ]

                delegate: GlassCard {
                    width: parent.width
                    implicitHeight: 80
                    activeFocusOnTab: true

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        Column {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: model.name
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }

                            Text {
                                text: model.desc
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }

                            Row {
                                spacing: MichiTheme.spacing.sm
                                visible: model.size !== "0 MB"

                                StatusBadge { text: model.size; kind: "info" }
                                StatusBadge { text: model.ram; kind: "info" }
                                StatusBadge { text: model.cpu; kind: "info" }
                            }
                        }

                        MichiButton {
                            id: actionBtn
                            text: {
                                if (root._selectedBackend === model.id) return "Activo"
                                if (model.status === "always") return "Siempre disponible"
                                if (root.ai && root.ai.backendType === model.id && root.ai.modelStatus === "loaded") return "Cargado"
                                if (root.ai && root.ai.backendType === model.id && root.ai.modelStatus === "downloading") return "Descargando..."
                                if (model.id === "sphynx") return "Usar Ollama"
                                var installed = root.ai ? root.ai.modelStatus : ""
                                if (installed === "installed" || installed === "loaded" || installed === "unloaded") return "Seleccionar"
                                return "Descargar"
                            }
                            variant: root._selectedBackend === model.id ? "primary" : "ghost"
                            enabled: {
                                if (model.status === "always") return false
                                if (root.ai && root.ai.modelStatus === "downloading" && root.ai.backendType === model.id) return false
                                return true
                            }
                            onClicked: {
                                if (!root.ai) return
                                if (root.ai.modelStatus === "downloading") return
                                var st = root.ai.modelStatus
                                if (st === "installed" || st === "loaded" || st === "unloaded" || model.id === "sphynx") {
                                    root.ai.setBackend(model.id)
                                    root._selectedBackend = model.id
                                } else if (model.id !== "calico" && model.id !== "sphynx") {
                                    root.ai.installModel(model.id)
                                    root._selectedBackend = model.id
                                    root.ai.setBackend(model.id)
                                }
                            }
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        visible: root.ai && root.ai.modelStatus === "downloading" && root._selectedBackend === model.id

                        ProgressBar {
                            width: 120
                            value: root._downloadProgress / 100
                        }

                        Text {
                            text: Math.round(root._downloadProgress) + "%"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        MichiButton {
                            text: "Cancelar"
                            variant: "ghost"
                            implicitHeight: 24
                            font.pixelSize: MichiTheme.typography.metaSize
                            onClicked: { if (root.ai) root.ai.cancelDownload() }
                        }
                    }
                    }

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Text {
                text: "Estado del backend activo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            GlassCard {
                width: parent.width
                implicitHeight: statusColumn.height + MichiTheme.spacing.lg * 2

                Column {
                    id: statusColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: "Backend: " + (root.ai ? root.ai.backendType : "—")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }

                    Text {
                        text: "Estado: " + (root.ai ? root.ai.modelStatus : "—")
                        color: root.ai && root.ai.modelStatus === "loaded" ? MichiTheme.colors.success :
                               root.ai && root.ai.modelStatus === "downloading" ? MichiTheme.colors.warning :
                               MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }

                    Text {
                        text: "RAM en uso: " + (root.ai ? root.ai.ramUsageMb + " MB" : "—")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.ai && root.ai.ramUsageMb > 0
                    }

                    ProgressBar {
                        width: parent.width
                        visible: root.ai && root.ai.modelStatus === "downloading"
                        value: root._downloadProgress / 100
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        visible: root.ai && root.ai.modelStatus === "loaded"

                        MichiButton {
                            text: "Liberar memoria"
                            variant: "ghost"
                            onClicked: { if (root.ai) root.ai.unloadModel() }
                        }

                        MichiButton {
                            text: "Probar backend"
                            variant: "secondary"
                            onClicked: {
                                if (root.ai) {
                                    var result = root.ai.runBenchmark()
                                    if (root.nav) root.nav.navigate("assistant")
                                }
                            }
                        }
                    }
                }
            }

            MichiButton {
                text: "Volver"
                variant: "ghost"
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: root.goBack()
            }
        }
    }
}
