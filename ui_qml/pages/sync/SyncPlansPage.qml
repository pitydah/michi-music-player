import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Planes de sincronización — visual plan editor concept.
 * The editor is a disabled preview: no plan contract exists yet, so
 * nothing can be saved and no plan is applied to any device.
 */
PlannedFeaturePage {
    id: root
    objectName: "syncPlansPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Planes de sincronización")

    featureTitle: qsTr("Planes de sincronización")
    featureDescription: qsTr("Define una vez qué se copia, a qué dispositivo y con qué reglas: contenido, listas, filtros y política de formato. El plan se reutiliza en cada sincronización.")
    featureIcon: "sync_plans"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Volver a Sincronización")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("sync")
    }

    SectionHeader { text: qsTr("Editor de plan (vista conceptual)") }

    GlassMaterial {
        width: root.contentWidth
        height: editorLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: editorLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Nombre del plan")
                    placeholderText: qsTr("p. ej. FiiO — lo esencial")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Dispositivo destino")
                    placeholderText: qsTr("Se seleccionará entre los detectados")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Origen")
                    placeholderText: qsTr("Biblioteca completa o carpeta")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Contenido")
                    placeholderText: qsTr("Todo, solo favoritos, selección…")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Listas de reproducción")
                    placeholderText: qsTr("Listas incluidas en el plan")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    label: qsTr("Reglas")
                    placeholderText: qsTr("Filtros por género, año, valoración…")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                MichiTextField {
                    Layout.fillWidth: true
                    Layout.columnSpan: 2
                    label: qsTr("Política de formato")
                    placeholderText: qsTr("Original si cabe; convertir a FLAC/MP3 según capacidad")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md

                MichiButton {
                    text: qsTr("Guardar plan")
                    variant: "primary"
                    tooltipText: qsTr("Se habilitará cuando exista el contrato de sincronización.")
                    enabled: false
                    opacity: MichiTheme.opacity.disabled
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Guardar está deshabilitado: todavía no existe el contrato que valida y persiste un plan.")
                    color: MichiTheme.colors.textTertiary
                    font.pixelSize: MichiTheme.typography.captionSize
                    wrapMode: Text.WordWrap
                    lineHeight: MichiTheme.typography.lineHeightBody
                }
            }
        }
    }

    GlassMaterial {
        width: root.contentWidth
        height: noteLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "accent"
        radius: MichiTheme.radius.md

        Text {
            id: noteLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            text: qsTr("Estado real: no hay planes guardados ni motor de sincronización para portátiles. Esta vista es un diseño conceptual del editor, sin datos ni acciones activas.")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.secondarySize
            wrapMode: Text.WordWrap
            lineHeight: MichiTheme.typography.lineHeightBody
        }
    }
}
