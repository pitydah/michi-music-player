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
    property string fileA: ""
    property string fileB: ""
    property var comparisonResult: null
    property string comparisonError: ""

    objectName: "audioComparison.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Comparación de audio"

    function swapFiles() {
        var tmp = root.fileA
        root.fileA = root.fileB
        root.fileB = tmp
    }

    function startComparison() {
        if (!root.labService || !root.fileA || !root.fileB) return
        root.pageState = "COMPARING"
        root.comparisonError = ""
        root.comparisonResult = null
        var result = root.labService.compareFiles(root.fileA, root.fileB)
        if (result && !result.error) {
            root.comparisonResult = result
            root.pageState = "COMPLETED"
        } else {
            root.comparisonError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function cancelComparison() {
        root.pageState = "INPUT_READY"
        root.comparisonResult = null
    }

    function selectFileA() {
        root.fileA = "/dummy/file_a.flac"
    }

    function selectFileB() {
        root.fileB = "/dummy/file_b.flac"
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioComparison.focusScope"
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
                    text: "Comparación de audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Comparación de audio"
                }

                Text {
                    text: "Compara formato, codec, bitrate, sample rate, bit depth, canales, tamaño, loudness, peak, metadatos, hash."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                SectionHeader { text: "Archivo A"; width: parent.width; objectName: "comparison.section.fileA" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.fileA ? "accent" : "base"
                    objectName: "comparison.fileA"
                    height: 60
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        Text { text: root.fileA || "(ninguno)"; color: root.fileA ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight; width: parent.width - 80 }
                        MichiButton { text: "Seleccionar"; variant: "ghost"; objectName: "comparison.selectFileA"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.selectFileA(); Accessible.name: "Seleccionar archivo A" }
                    }
                }

                SectionHeader { text: "Archivo B"; width: parent.width; objectName: "comparison.section.fileB" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.fileB ? "accent" : "base"
                    objectName: "comparison.fileB"
                    height: 60
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        Text { text: root.fileB || "(ninguno)"; color: root.fileB ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight; width: parent.width - 80 }
                        MichiButton { text: "Seleccionar"; variant: "ghost"; objectName: "comparison.selectFileB"; anchors.verticalCenter: parent.verticalCenter; onClicked: root.selectFileB(); Accessible.name: "Seleccionar archivo B" }
                    }
                }

                SectionHeader { text: "Dimensiones de comparación"; width: parent.width; objectName: "comparison.section.dimensions" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "comparison.dimensions"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        Repeater {
                            model: root.comparisonResult && root.comparisonResult.dimensions ? root.comparisonResult.dimensions : [
                                {key:"format", label:"Formato", identical:true},
                                {key:"codec", label:"Codec", identical:true},
                                {key:"bitrate", label:"Bitrate", identical:true},
                                {key:"sample_rate", label:"Sample Rate", identical:true},
                                {key:"bit_depth", label:"Bit Depth", identical:true},
                                {key:"channels", label:"Canales", identical:true},
                                {key:"size", label:"Tamaño", identical:true},
                                {key:"loudness", label:"Loudness", identical:true},
                                {key:"peak", label:"Peak", identical:true},
                                {key:"metadata", label:"Metadata", identical:true},
                                {key:"hash", label:"Hash", identical:true},
                                {key:"integrity", label:"Integridad", identical:true}
                            ]
                            Row {
                                spacing: MichiTheme.spacing.sm
                                Text { text: model.label; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: 120 }
                                Text { text: model.identical !== undefined ? (model.identical ? "✓ Igual" : "✗ Diferente") : "—"; color: model.identical !== undefined ? (model.identical ? MichiTheme.colors.success : MichiTheme.colors.warning) : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 120 }
                            }
                        }
                    }
                }

                SectionHeader { text: "Acciones"; width: parent.width; objectName: "comparison.section.actions" }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.pageState === "COMPARING" ? "Cancelar" : "Comparar"
                        variant: root.pageState === "COMPARING" ? "danger" : "primary"
                        objectName: root.pageState === "COMPARING" ? "comparison.cancelBtn" : "comparison.startBtn"
                        enabled: root.fileA !== "" && root.fileB !== "" && root.pageState !== "COMPARING"
                        onClicked: { if (root.pageState === "COMPARING") root.cancelComparison(); else root.startComparison() }
                        Accessible.name: root.pageState === "COMPARING" ? "Cancelar comparación" : "Iniciar comparación"
                    }
                    MichiButton {
                        text: "Intercambiar A/B"
                        variant: "secondary"
                        objectName: "comparison.swapBtn"
                        onClicked: root.swapFiles()
                        Accessible.name: "Intercambiar archivos A y B"
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "comparison.backBtn"
                        enabled: root.pageState !== "COMPARING"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : "status"
                    objectName: "comparison.results"
                    height: 60
                    Text {
                        anchors.centerIn: parent
                        text: root.pageState === "COMPARING" ? "Comparando..." : (root.pageState === "COMPLETED" ? (root.comparisonResult && root.comparisonResult.identical ? "Los archivos son idénticos" : "Los archivos difieren") : (root.pageState === "FAILED" ? "Error: " + root.comparisonError : "Selecciona dos archivos para comparar"))
                        color: root.pageState === "FAILED" ? MichiTheme.colors.error : (root.pageState === "COMPLETED" && root.comparisonResult && root.comparisonResult.identical ? MichiTheme.colors.success : MichiTheme.colors.textMuted)
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
