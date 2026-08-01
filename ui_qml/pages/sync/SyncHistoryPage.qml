import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Historial de sincronización — premium timeline concept.
 * The timeline entry is a labeled conceptual example with empty values;
 * the empty state below is the real state of this installation.
 */
PlannedFeaturePage {
    id: root
    objectName: "syncHistoryPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Historial de sincronización")

    featureTitle: qsTr("Historial de sincronización")
    featureDescription: qsTr("Cada sincronización dejará un registro auditable: dispositivo, fecha, duración, pistas transferidas, errores y resultado final. Nada se moverá sin que puedas revisarlo después.")
    featureIcon: "sync_history"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Volver a Sincronización")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("sync")
    }

    SectionHeader { text: qsTr("Resultados que se registrarán") }

    GlassMaterial {
        width: root.contentWidth
        height: legendLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: legendLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    { label: qsTr("Completada"), kind: "success", text: qsTr("Todo el plan se transfirió sin errores.") },
                    { label: qsTr("Parcial"), kind: "warning", text: qsTr("Parte del contenido quedó fuera; el detalle dirá cuál y por qué.") },
                    { label: qsTr("Cancelada"), kind: "info", text: qsTr("La detuvo el usuario; lo ya copiado queda registrado.") },
                    { label: qsTr("Fallida"), kind: "error", text: qsTr("No se pudo completar; el registro incluirá el error y los pasos sugeridos.") }
                ]

                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md

                    StatusBadge {
                        Layout.alignment: Qt.AlignTop
                        text: modelData.label
                        kind: modelData.kind
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

            Text {
                Layout.fillWidth: true
                text: qsTr("La propia vista también tendrá estados: vacía, cargando, con error de lectura y con datos.")
                color: MichiTheme.colors.textTertiary
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }

    SectionHeader { text: qsTr("Así se verá cada registro") }

    GlassMaterial {
        width: root.contentWidth
        height: entryLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "hero"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: entryLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md

                MichiIcon {
                    Layout.alignment: Qt.AlignTop
                    iconKey: "sync_history"
                    size: MichiTheme.iconSizeLarge
                    color: MichiTheme.colors.textSecondary
                    accessibleName: qsTr("Registro conceptual")
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.xs

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Ejemplo conceptual — sin datos reales")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: MichiTheme.spacing.xl
                        rowSpacing: MichiTheme.spacing.xs

                        Repeater {
                            model: [
                                { key: qsTr("Dispositivo"), value: "—" },
                                { key: qsTr("Fecha"), value: "—" },
                                { key: qsTr("Duración"), value: "—" },
                                { key: qsTr("Transferidas"), value: "—" },
                                { key: qsTr("Errores"), value: "—" },
                                { key: qsTr("Resultado"), value: "—" }
                            ]

                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.sm

                                Text {
                                    text: modelData.key + ":"
                                    color: MichiTheme.colors.textTertiary
                                    font.pixelSize: MichiTheme.typography.secondarySize
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.value
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.secondarySize
                                }
                            }
                        }
                    }
                }

                StatusBadge {
                    Layout.alignment: Qt.AlignTop
                    text: qsTr("Conceptual")
                    kind: "info"
                }
            }
        }
    }

    MichiEmptyState {
        width: root.contentWidth
        title: qsTr("Sin sincronizaciones registradas")
        message: qsTr("Estado real: todavía no existe el registro de sincronización. Cuando la función esté disponible, cada operación aparecerá aquí con su resultado.")
        iconName: "sync_history"
    }
}
