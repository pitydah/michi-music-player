import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string bridgeState: root.alab ? "READY" : "NO_BRIDGE"

    objectName: "audioLab.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Audio Lab"
    Accessible.description: "Análisis técnico, conversión, normalización, integridad y comparación de archivos de audio"

    Component.onCompleted: {
        if (root.alab && typeof root.alab.refresh !== "undefined")
            root.alab.refresh()
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioLab.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.navigate("home")
        }

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "audioLab.flickableContent"

            Keys.onEscapePressed: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home")
            }

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: hero
                    width: parent.width
                    height: 150
                    radius: MichiTheme.radiusLg
                    showGlow: true
                    objectName: "audioLab.hero"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xl
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Audio Lab"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            Accessible.role: Accessible.Heading
                            Accessible.name: "Audio Lab"
                        }

                        Text {
                            text: "Análisis técnico, conversión, normalización, integridad y comparación de archivos de audio."
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width * 0.75
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                AudioSelectionSummary {
                    id: selectionSummary
                    objectName: "audioLab.selectionSummary"
                    Accessible.name: "Resumen de selección de audio"
                }

                SectionHeader {
                    id: toolsSection
                    text: "Herramientas"
                    width: parent.width
                    objectName: "audioLab.section.tools"
                    Accessible.name: "Sección de herramientas"
                    KeyNavigation.tab: toolsGrid
                }

                Grid {
                    id: toolsGrid
                    width: parent.width
                    columns: 2
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md
                    objectName: "audioLab.toolsGrid"

                    Repeater {
                        id: toolsRepeater
                        model: root.alab && root.alab.tools ? root.alab.tools : []

                        delegate: GlassCard {
                            width: (parent.width - MichiTheme.spacing.md) / 2
                            height: 110
                            title: model.label
                            subtitle: {
                                if (model.toolState === "LOADING") return "Cargando..."
                                if (model.toolState === "ERROR") return "No disponible"
                                return model.desc
                            }
                            variant: model.toolState === "ERROR" ? "danger" : model.cardVariant
                            objectName: "audioLab.tool." + model.toolId
                            Accessible.name: model.label
                            Accessible.description: {
                                if (model.toolState === "LOADING") return "Cargando " + model.label
                                if (model.toolState === "ERROR") return model.label + " no disponible"
                                return model.desc
                            }
                            opacity: model.toolState === "ERROR" ? 0.6 : 1.0
                            interactive: model.toolState === "READY"
                            focusPolicy: Qt.StrongFocus
                            KeyNavigation.tab: index + 1 < toolsRepeater.count ? toolsRepeater.itemAt(index + 1) : backendSection

                            onClicked: {
                                if (model.toolState !== "READY") return
                                var routeMap = {
                                    "analysis": "audio_lab_analysis",
                                    "conversion": "audio_lab_conversion",
                                    "normalization": "audio_lab_normalization",
                                    "replaygain": "audio_lab_replaygain",
                                    "integrity": "audio_lab_integrity",
                                    "comparison": "audio_lab_comparison",
                                    "jobs": "audio_lab_jobs",
                                    "profiles": "audio_lab_profiles"
                                }
                                var route = routeMap[model.toolId]
                                if (route && root.nav) root.nav.navigate(route)
                            }

                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()

                            Row {
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                anchors.margins: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.xs
                                visible: model.toolState !== "READY"

                                StatusBadge {
                                    text: model.toolState === "LOADING" ? "Cargando" : "No disponible"
                                    kind: model.toolState === "LOADING" ? "info" : "error"
                                }
                            }
                        }
                    }
                }

                SectionHeader {
                    id: backendSection
                    text: "Estado del backend"
                    width: parent.width
                    objectName: "audioLab.section.backend"
                    Accessible.name: "Sección de estado del backend"
                }

                GlassMaterial {
                    width: parent.width
                    radius: MichiTheme.radiusMd
                    variant: "base"
                    objectName: "audioLab.backendInfo"
                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm
                        Text {
                            text: "Backend: " + (root.alab ? (root.alab.backendInfo ? root.alab.backendInfo.backend : "no disponible") : "no disponible")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                        Text {
                            text: "Pipeline: " + (root.alab ? (root.alab.pipelineInfo ? JSON.stringify(root.alab.pipelineInfo) : "") : "")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }

                GlassMaterial {
                    width: parent.width
                    radius: MichiTheme.radiusMd
                    variant: "status"
                    objectName: "audioLab.statusInfo"
                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm
                        StatusBadge { text: "Experimental"; kind: "experimental" }
                        StatusBadge { text: "Requiere ffmpeg para conversión"; kind: "info" }
                    }
                }
            }
        }
    }
}
