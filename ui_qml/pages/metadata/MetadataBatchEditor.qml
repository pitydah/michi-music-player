import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Batch Editor"
    objectName: "metadataBatchEditor"
    focus: true
    id: root

    property var mb: null
    property var selectedFiles: []
    property bool _confirmApply: false

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.lg

        SectionHeader { text: "Edición por lotes"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                Text { text: root.selectedFiles.length + " archivos seleccionados"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                Text { text: "Buscar y reemplazar"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: "Campo:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: searchField; width: parent.width - 70; placeholderText: "artist, title, album..." }
                }
                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: "Buscar:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: searchText; width: parent.width - 70; placeholderText: "Valor a buscar..." }
                }
                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: "Reemplazar:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: replaceText; width: parent.width - 70; placeholderText: "Valor nuevo..." }
                }
                MichiButton {
                    text: "Ejecutar búsqueda y reemplazo"
                    variant: "secondary"
                    onClicked: {
                        if (root.mb && searchText.text && replaceText.text && searchField.text)
                            root.mb.batchSetField(root.selectedFiles, searchField.text, replaceText.text)
                    }
                }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                Text { text: "Numeración"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: "Inicio:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter }
                    SpinBox { id: numberingStart; from: 1; to: 999; value: 1 }
                    MichiButton { text: "Numerar pistas"; variant: "secondary"; onClicked: {
                        if (root.mb) root.mb.batchSetField(root.selectedFiles, "track_number", String(numberingStart.value))
                    } }
                }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: "Disco inicio:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter }
                    SpinBox { id: discStart; from: 1; to: 99; value: 1 }
                    MichiButton { text: "Numerar discos"; variant: "secondary"; onClicked: {
                        if (root.mb) root.mb.batchSetField(root.selectedFiles, "disc_number", String(discStart.value))
                    } }
                }
            }
        }

        MetadataDiffView {
            width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm
            MichiButton {
                text: root._confirmApply ? "Confirmar aplicar lotes" : "Aplicar cambios"
                variant: root._confirmApply ? "danger" : "primary"
                onClicked: {
                    if (!root._confirmApply) {
                        root._confirmApply = true
                    } else {
                        root._confirmApply = false
                    }
                }
            }
            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                visible: root._confirmApply
                onClicked: root._confirmApply = false
            }
        }

        MetadataWriteProgress {
            width: parent.width
            mb: root.mb
        }
    }
}
