import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Michi Big Server — product concept page.
 * Big Server is a future project: no server exists, nothing to configure,
 * no data to show. The diagram and pillars describe the vision only.
 */
PlannedFeaturePage {
    id: root
    objectName: "bigServerPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi Big Server")

    featureTitle: qsTr("Michi Big Server")
    featureDescription: qsTr("Un servidor doméstico que centralice tu biblioteca, aplique el motor audiófilo de Michi y sirva música a todo el ecosistema: este reproductor, el móvil, las zonas de la casa y clientes remotos.")
    featureIcon: "big_server"
    featureState: "planned"
    statusLabel: qsTr("Concepto de producto")
    statusKind: "info"
    primaryActionText: qsTr("Volver a Conexiones")
    secondaryActionText: qsTr("Ver Micro Server")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("connections")
    }
    onSecondaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("connections.micro_server")
    }

    component DiagramNode: GlassMaterial {
        property string nodeIcon: "library"
        property string nodeLabel: ""
        property bool emphasized: false

        radius: MichiTheme.radius.md
        variant: emphasized ? "accent" : "status"
        implicitWidth: nodeRow.implicitWidth + MichiTheme.spacing.lg * 2
        implicitHeight: nodeRow.implicitHeight + MichiTheme.spacing.md * 2

        RowLayout {
            id: nodeRow
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.sm

            MichiIcon {
                iconKey: nodeIcon
                size: MichiTheme.iconSizeRegular
                color: emphasized ? MichiTheme.colors.accentPrimary
                                  : MichiTheme.colors.textSecondary
                accessibleName: nodeLabel
            }

            Text {
                text: nodeLabel
                color: emphasized ? MichiTheme.colors.textPrimary
                                  : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                font.weight: emphasized ? MichiTheme.typography.weightSemiBold
                                        : MichiTheme.typography.weightMedium
            }
        }
    }

    component DiagramLink: Rectangle {
        Layout.alignment: Qt.AlignVCenter
        implicitWidth: 28
        implicitHeight: 2
        radius: 1
        color: MichiTheme.colors.accentSeparator
    }

    component PillarCard: GlassMaterial {
        property string pillarIcon: "library"
        property string pillarTitle: ""
        property string pillarText: ""

        Layout.fillWidth: true
        Layout.minimumWidth: 200
        implicitHeight: pillarLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: pillarLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            MichiIcon {
                iconKey: pillarIcon
                size: MichiTheme.iconSizeLarge
                color: MichiTheme.colors.accentPrimary
                accessibleName: pillarTitle
            }

            Text {
                Layout.fillWidth: true
                text: pillarTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: pillarText
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }

    SectionHeader { text: qsTr("Cómo encajaría en tu red") }

    GlassMaterial {
        width: root.contentWidth
        height: diagramLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "hero"
        radius: MichiTheme.radius.md

        RowLayout {
            id: diagramLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            DiagramNode {
                            Layout.alignment: Qt.AlignVCenter
                            nodeIcon: "library"; nodeLabel: qsTr("Biblioteca") }
            DiagramLink {}
            DiagramNode {
                            Layout.alignment: Qt.AlignVCenter
                            nodeIcon: "big_server"; nodeLabel: qsTr("Big Server"); emphasized: true }
            DiagramLink {}

            ColumnLayout {
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.sm

                DiagramNode { nodeIcon: "home"; nodeLabel: qsTr("Player") }
                DiagramNode { nodeIcon: "mobile"; nodeLabel: qsTr("Mobile") }
                DiagramNode { nodeIcon: "rooms"; nodeLabel: qsTr("Zonas") }
                DiagramNode { nodeIcon: "connections"; nodeLabel: qsTr("Remoto") }
            }
        }
    }

    SectionHeader { text: qsTr("Tres pilares del concepto") }

    RowLayout {
        width: root.contentWidth
        spacing: MichiTheme.spacing.md

        PillarCard {
            pillarIcon: "library"
            pillarTitle: qsTr("Biblioteca central")
            pillarText: qsTr("Una sola biblioteca indexada en el servidor: mismos metadatos, mismas carátulas y mismo historial en todos los clientes.")
        }

        PillarCard {
            pillarIcon: "eq"
            pillarTitle: qsTr("Motor audiófilo")
            pillarText: qsTr("La cadena de audio de Michi ejecutada en el servidor: perfiles de salida, DSP y bit-perfecto sin duplicar ajustes por equipo.")
        }

        PillarCard {
            pillarIcon: "distribution"
            pillarTitle: qsTr("Ecosistema distribuido")
            pillarText: qsTr("Player de escritorio, móvil, zonas multiroom y acceso remoto como clientes del mismo servidor, cada uno con sus capacidades.")
        }
    }

    GlassMaterial {
        width: root.contentWidth
        height: stateLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "accent"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: stateLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                Layout.fillWidth: true
                text: qsTr("Estado real: proyecto futuro")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Big Server no está implementado: no hay servidor que instalar, puertos que abrir ni clientes conectados. Lo que sí existe hoy es Michi Micro Server para descubrimiento en red local.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }
}
