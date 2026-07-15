import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string pageState: "INPUT_READY"
    property bool bridgeAvailable: root.labService !== null
    property var analysisResult: null
    property string analysisError: ""

    objectName: "audioAnalysis.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Análisis técnico"

    function startAnalysis() {
        if (!root.labService) return
        root.pageState = "ANALYSING"
        root.analysisError = ""
        root.analysisResult = null
        var result = root.labService.analyzeFile("/dummy")
        if (result && result.status !== "error") {
            root.analysisResult = result
            root.pageState = "COMPLETED"
        } else {
            root.analysisError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function cancelAnalysis() {
        root.pageState = "INPUT_READY"
        root.analysisResult = null
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioAnalysis.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
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

                Text {
                    text: "Análisis técnico"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Análisis técnico"
                }

                Text {
                    text: "Formato, codec, bitrate, sample rate, bit depth, canales, loudness, peak, checksum."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                AudioInputSelection {}

                SectionHeader { text: "Resultado del análisis"; width: parent.width; objectName: "analysis.section.result" }

                AudioTechnicalReport {
                    width: parent.width
                    analysisResult: root.analysisResult
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : "base"
                    objectName: "analysis.resultArea"
                    height: root.analysisResult ? 100 : 80
                    visible: root.pageState === "COMPLETED" || root.pageState === "FAILED"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        visible: root.analysisResult !== null
                        Repeater {
                            model: root.analysisResult ? Object.keys(root.analysisResult).filter(function(k) { return k !== "filepath" }).slice(0, 8) : []
                            Row {
                                spacing: MichiTheme.spacing.sm
                                Text { text: modelData + ": "; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: 120 }
                                Text { text: root.analysisResult ? String(root.analysisResult[modelData]) : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }
                            }
                        }
                        Text { text: "Error: " + root.analysisError; color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; visible: root.pageState === "FAILED" }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: root.pageState === "ANALYSING" ? "Analizando..." : (root.pageState === "FAILED" ? "Error en el análisis" : "Selecciona archivos para analizar")
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.analysisResult === null && root.pageState !== "ANALYSING"
                    }

                    MichiProgressBar { width: 200; anchors.centerIn: parent; indeterminate: true; visible: root.pageState === "ANALYSING" }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.pageState === "ANALYSING" ? "Cancelar" : "Analizar selección"
                        variant: root.pageState === "ANALYSING" ? "danger" : "primary"
                        objectName: root.pageState === "ANALYSING" ? "analysis.cancelBtn" : "analysis.startBtn"
                        enabled: root.pageState !== "COMPLETED"
                        onClicked: {
                            if (root.pageState === "ANALYSING") root.cancelAnalysis()
                            else root.startAnalysis()
                        }
                        Accessible.name: root.pageState === "ANALYSING" ? "Cancelar análisis" : "Iniciar análisis"
                    }
                    MichiButton {
                        text: "Comparar con otro archivo"
                        variant: "secondary"
                        objectName: "analysis.compareBtn"
                        enabled: root.analysisResult !== null
                        onClicked: { if (root.nav) root.nav.navigate("audio_lab_comparison") }
                        Accessible.name: "Comparar con otro archivo"
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "analysis.backBtn"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }
            }
        }
    }
}
