import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Reproductores portátiles — planned sync target.
 * Device classes, the conceptual device card and the transfer area are
 * vision only. The empty state is real: no player is detected because
 * the feature is not implemented.
 */
PlannedFeaturePage {
    id: root
    objectName: "portablePlayersPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Reproductores portátiles")

    featureTitle: qsTr("Reproductores portátiles")
    featureDescription: qsTr("Sincroniza tu biblioteca con reproductores dedicados (FiiO, HiBy) y con cualquier dispositivo USB de almacenamiento masivo (MSC) o MTP, con planes de contenido y conversión bajo demanda.")
    featureIcon: "portable_player"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Volver a Sincronización")
    secondaryActionText: qsTr("Dispositivos móviles")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("sync")
    }
    onSecondaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("sync.mobile")
    }

    SectionHeader { text: qsTr("Dispositivos que se admitirán") }

    RowLayout {
        width: root.contentWidth
        spacing: MichiTheme.spacing.md

        Repeater {
            model: [
                { icon: "portable_player", title: qsTr("DAP dedicados"), text: qsTr("FiiO, HiBy y similares montados como unidad USB.") },
                { icon: "devices", title: qsTr("USB MSC"), text: qsTr("Cualquier dispositivo de almacenamiento masivo con carpeta de destino.") },
                { icon: "mobile", title: qsTr("MTP"), text: qsTr("Dispositivos de protocolo MTP con transferencia gestionada.") }
            ]

            delegate: GlassMaterial {
                required property var modelData
                Layout.fillWidth: true
                Layout.minimumWidth: 180
                implicitHeight: classLayout.implicitHeight + MichiTheme.spacing.lg * 2
                variant: "status"
                radius: MichiTheme.radius.md

                ColumnLayout {
                    id: classLayout
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    MichiIcon {
                        iconKey: modelData.icon
                        size: MichiTheme.iconSizeLarge
                        color: MichiTheme.colors.accentPrimary
                        accessibleName: modelData.title
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.text
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        wrapMode: Text.WordWrap
                        lineHeight: MichiTheme.typography.lineHeightBody
                    }
                }
            }
        }
    }

    SectionHeader { text: qsTr("Así se verá un dispositivo conectado") }

    GlassMaterial {
        width: root.contentWidth
        height: deviceLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "hero"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: deviceLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md

                MichiIcon {
                    iconKey: "portable_player"
                    size: 32
                    color: MichiTheme.colors.textSecondary
                    accessibleName: qsTr("Dispositivo conceptual")
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.xxs

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Reproductor USB — vista conceptual")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Capacidad: — · Libre: — · Plan: —")
                        color: MichiTheme.colors.textTertiary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        wrapMode: Text.WordWrap
                    }
                }

                StatusBadge {
                    Layout.alignment: Qt.AlignTop
                    text: qsTr("Conceptual")
                    kind: "info"
                }
            }

            MichiProgressBar {
                Layout.fillWidth: true
                value: 0
                accessibleName: qsTr("Progreso de transferencia: sin transferencias activas")
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Sin transferencias activas. La barra mostrará el progreso real cuando la sincronización con portátiles exista.")
                color: MichiTheme.colors.textTertiary
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
            }
        }
    }

    MichiEmptyState {
        width: root.contentWidth
        title: qsTr("Ningún reproductor detectado")
        message: qsTr("Estado real: la detección de reproductores portátiles no está implementada. Cuando lo esté, los dispositivos conectados por USB aparecerán aquí automáticamente.")
        iconName: "portable_player"
    }
}
