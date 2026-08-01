import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioLabHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Audio Lab")

    // Canonical Audio Lab areas. Routes must exist in
    // ui_qml_bridge/route_registry.py (sidebar_visible: false — hub-only).
    readonly property var areas: [
        {
            "key": "diagnostics",
            "title": qsTr("Diagnóstico"),
            "description": qsTr("Analiza la cadena de audio, formatos y salida bit-perfect."),
            "iconKey": "analysis",
            "route": "audio_lab.diagnostics",
            "capability": "audio_lab",
            "status": "functional",
            "statusText": qsTr("Disponible"),
            "metadataText": qsTr("GStreamer · MPD · DAC")
        },
        {
            "key": "identifier",
            "title": qsTr("Identificador de Audios"),
            "description": qsTr("Reconoce pistas y completa sus metadatos automáticamente."),
            "iconKey": "search",
            "route": "audio_lab.identifier",
            "capability": "metadata",
            "status": "functional",
            "statusText": qsTr("Disponible"),
            "metadataText": qsTr("Shazam · AudD · AcoustID")
        },
        {
            "key": "backup",
            "title": qsTr("Respaldar"),
            "description": qsTr("Crea copias de seguridad de tu biblioteca y configuración."),
            "iconKey": "folders",
            "route": "audio_lab.backup",
            "capability": "audio_lab",
            "status": "functional",
            "statusText": qsTr("Disponible"),
            "metadataText": qsTr("Biblioteca + ajustes")
        },
        {
            "key": "output_profiles",
            "title": qsTr("Perfiles de Salida"),
            "description": qsTr("Configura perfiles de salida de audio para cada dispositivo."),
            "iconKey": "outputs",
            "route": "audio_lab.output_profiles",
            "capability": "output_profiles",
            "status": "functional",
            "statusText": qsTr("Disponible"),
            "metadataText": qsTr("GStreamer · MPD")
        },
        {
            "key": "local_intelligence",
            "title": qsTr("Inteligencia local"),
            "description": qsTr("Mixes inteligentes y recomendaciones generadas en tu equipo."),
            "iconKey": "ai",
            "route": "audio_lab.local_intelligence",
            "capability": "mix",
            "status": "functional",
            "statusText": qsTr("Disponible"),
            "metadataText": qsTr("100% local · privado")
        }
    ]

    function capabilityAvailable(cap) {
        if (typeof capabilityBridge === "undefined" || !capabilityBridge)
            return true
        if (typeof capabilityBridge.has === "function")
            return capabilityBridge.has(cap)
        return true
    }

    function openArea(route) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate(route)
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
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
                        text: qsTr("Audio Lab")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Herramientas profesionales para diagnosticar, identificar, respaldar y configurar tu audio.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Areas")
                width: parent.width
            }

            // Superior grid: 3 cards
            Grid {
                id: topGrid
                width: parent.width
                columns: 3
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.areas.slice(0, 3)

                    MichiFeatureCard {
                        required property var modelData
                        width: (topGrid.width - 2 * MichiTheme.spacing.md) / 3
                        title: modelData.title
                        description: modelData.description
                        iconKey: modelData.iconKey
                        route: modelData.route
                        capability: modelData.capability
                        capabilityAvailable: root.capabilityAvailable(modelData.capability)
                        status: modelData.status
                        statusText: modelData.statusText
                        metadataText: modelData.metadataText
                        primaryActionText: qsTr("Abrir")
                        featureAccessibleName: modelData.title
                        activeFocusOnTab: true
                        onClicked: root.openArea(modelData.route)
                    }
                }
            }

            // Inferior grid: 2 cards centered
            Item {
                width: parent.width
                height: bottomRow.height

                Row {
                    id: bottomRow
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.areas.slice(3, 5)

                        MichiFeatureCard {
                            required property var modelData
                            width: (topGrid.width - 2 * MichiTheme.spacing.md) / 3
                            title: modelData.title
                            description: modelData.description
                            iconKey: modelData.iconKey
                            route: modelData.route
                            capability: modelData.capability
                            capabilityAvailable: root.capabilityAvailable(modelData.capability)
                            status: modelData.status
                            statusText: modelData.statusText
                            metadataText: modelData.metadataText
                            primaryActionText: qsTr("Abrir")
                            featureAccessibleName: modelData.title
                            activeFocusOnTab: true
                            onClicked: root.openArea(modelData.route)
                        }
                    }
                }
            }
        }
    }
}
