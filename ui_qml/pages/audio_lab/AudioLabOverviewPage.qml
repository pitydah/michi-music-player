import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab Overview"
    objectName: "audioLabOverviewPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: root.alab && root.alab.backendInfo && root.alab.backendInfo.available ? 1 : 0

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2

    Component.onCompleted: {
        root.pageState = "READY"
        if (root.alab && typeof root.alab.refresh !== "undefined")
            root.alab.refresh()
        alabGuard.checkCapability(root.alab)
    }

    CapabilityGuard {
        anchors.fill: parent
        capabilityName: "audio_lab"

        Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 150; radius: MichiTheme.radius.lg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Audio Lab"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Análisis técnico, conversión, normalización, integridad y comparación de archivos de audio."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.75; wrapMode: Text.WordWrap
                    }
                }
            }

            AudioSelectionSummary { id: selectionSummary }

            SectionHeader { text: "Herramientas"; width: parent.width; objectName: "toolsHeader"; Accessible.name: "Herramientas" }

            StatusBadge {
                text: root._state === root.stateLoading ? "Cargando..." : root._state === root.stateReady ? "Disponible" : "No disponible"
                kind: root._state === root.stateReady ? "success" : root._state === root.stateLoading ? "info" : "error"
            }

            Grid {
                width: parent.width; columns: 2; columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Análisis técnico"
                    subtitle: "Formato, codec, bitrate, calidad"
                    variant: root._state === root.stateReady ? "accent" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.analysis") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Conversión"
                    subtitle: "FLAC, MP3, AAC, Opus, WAV"
                    variant: root._state === root.stateReady ? "accent" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.conversion") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Normalización"
                    subtitle: "Loudness, pico, ganancia"
                    variant: root._state === root.stateReady ? "base" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.normalization") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "ReplayGain"
                    subtitle: "Etiquetas de ganancia"
                    variant: root._state === root.stateReady ? "base" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.replaygain") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Integridad"
                    subtitle: "Cabeceras, corrupción, checksum"
                    variant: root._state === root.stateReady ? "status" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.integrity") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Comparación"
                    subtitle: "Diferencias entre variantes"
                    variant: root._state === root.stateReady ? "status" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.comparison") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Trabajos"
                    subtitle: "Cola y estado de procesos"
                    variant: root._state === root.stateReady ? "base" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.jobs") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Perfiles"
                    subtitle: "Presets de conversión"
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab.profiles") }
                }
            }

            SectionHeader { text: "Estado del backend"; width: parent.width; objectName: "backendHeader"; Accessible.name: "Estado del backend" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: "Backend: " + (root.alab ? (root.alab.backendInfo ? root.alab.backendInfo.backend : "no disponible") : "no disponible"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: "Pipeline: " + (root.alab ? (root.alab.pipelineInfo ? JSON.stringify(root.alab.pipelineInfo) : "") : ""); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Requiere ffmpeg para conversión"; kind: "info"; objectName: "ffmpegBadge" }
                }
            }

            StatusBadge {
                visible: root.alab === null
                text: "Bridge no disponible"
                kind: "disconnected"
            }
        }
    }
}
}
