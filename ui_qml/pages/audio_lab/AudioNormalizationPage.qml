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
    property real targetLufs: -14.0
    property real truePeakLimit: -1.0
    property var normResult: null
    property string normError: ""

    objectName: "audioNormalization.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Normalización"

    function startPreview() {
        if (!root.labService) return
        root.pageState = "PREVIEWING"
        root.normError = ""
        root.normResult = null
        var result = root.labService.startNormalization("/dummy")
        if (result && result.ok) {
            root.normResult = result
            root.pageState = "PREVIEWING"
        } else {
            root.normError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function applyNormalization() {
        if (!root.labService) return
        root.pageState = "APPLYING"
    }

    function cancelOperation() {
        root.pageState = "INPUT_READY"
        root.normResult = null
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioNormalization.focusScope"
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
                    text: "Normalización"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Normalización"
                }

                Text {
                    text: "Ajuste de loudness según estándar LUFS. No destructivo a menos que se aplique."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                AudioInputSelection {}
                AudioSelectionSummary { width: parent.width }

                SectionHeader { text: "Parámetros de normalización"; width: parent.width; objectName: "normalization.section.params" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "normalization.params"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Column {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "LUFS objetivo: " + root.targetLufs.toFixed(1); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                            MichiSlider {
                                id: lufsSlider
                                objectName: "normalization.targetLufsSlider"
                                width: parent.width; from: -30; to: -8; value: root.targetLufs; stepSize: 0.5
                                accessibleName: "LUFS objetivo"
                                onMoved: function(v) { root.targetLufs = v }
                            }
                        }

                        Column {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "Límite de pico verdadero: " + root.truePeakLimit.toFixed(1) + " dBTP"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                            MichiSlider {
                                id: truePeakSlider
                                objectName: "normalization.truePeakSlider"
                                width: parent.width; from: -6; to: 0; value: root.truePeakLimit; stepSize: 0.1
                                accessibleName: "Límite de pico verdadero"
                                onMoved: function(v) { root.truePeakLimit = v }
                            }
                        }
                    }
                }

                SectionHeader { text: "Acciones"; width: parent.width; objectName: "normalization.section.actions" }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.pageState === "PREVIEWING" ? "Cancelar" : "Previsualizar"
                        variant: root.pageState === "PREVIEWING" ? "danger" : "secondary"
                        objectName: root.pageState === "PREVIEWING" ? "normalization.cancelBtn" : "normalization.previewBtn"
                        enabled: root.pageState !== "APPLYING"
                        onClicked: { if (root.pageState === "PREVIEWING") root.cancelOperation(); else root.startPreview() }
                        Accessible.name: root.pageState === "PREVIEWING" ? "Cancelar previsualización" : "Previsualizar normalización"
                    }
                    MichiButton {
                        text: "Aplicar"
                        variant: "primary"
                        objectName: "normalization.applyBtn"
                        enabled: root.pageState === "PREVIEWING" || root.pageState === "COMPLETED"
                        onClicked: root.applyNormalization()
                        Accessible.name: "Aplicar normalización"
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "normalization.backBtn"
                        enabled: root.pageState !== "APPLYING"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }

                SectionHeader { text: "Resultados"; width: parent.width; objectName: "normalization.section.results" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : "status"
                    objectName: "normalization.results"
                    height: 80
                    Text {
                        anchors.centerIn: parent
                        text: root.pageState === "PREVIEWING" ? "Previsualizando..." : (root.pageState === "APPLYING" ? "Aplicando normalización..." : (root.pageState === "FAILED" ? "Error: " + root.normError : "Selecciona archivos para normalizar"))
                        color: root.pageState === "FAILED" ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        width: parent.width - MichiTheme.spacing.xl * 2
                    }
                }
            }
        }
    }
}
