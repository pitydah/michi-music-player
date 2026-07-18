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

        SectionHeader { text: qsTr("Edición por lotes"); width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                Text { text: root.selectedFiles.length + " archivos seleccionados"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "primary"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                Text { text: qsTr("Buscar y reemplazar"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("Campo:"); color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: searchField; width: parent.width - 70; placeholderText: qsTr("artist, title, album...") }
                        focusPolicy: Qt.StrongFocus
                }
                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("Buscar:"); color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: searchText; width: parent.width - 70; placeholderText: qsTr("Valor a buscar...") }
                        focusPolicy: Qt.StrongFocus
                }
                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("Reemplazar:"); color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                    TextField { id: replaceText; width: parent.width - 70; placeholderText: qsTr("Valor nuevo...") }
                        focusPolicy: Qt.StrongFocus
                }
                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: qsTr("Ejecutar búsqueda y reemplazo")
                    variant: "secondary"
                    onClicked: {
                        if (root.mb && searchText.text && replaceText.text && searchField.text)
                            root.mb.batchSetField(root.selectedFiles, searchField.text, replaceText.text)
                    }
                }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                Text { text: qsTr("Numeración"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("Inicio:"); color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter }
                    SpinBox { id: numberingStart; from: 1; to: 999; value: 1 }
                        focusPolicy: Qt.StrongFocus
                    MichiButton { text: qsTr("Numerar pistas"); variant: "secondary"; onClicked: {
                        if (root.mb) root.mb.batchSetField(root.selectedFiles, "track_number", String(numberingStart.value))
                    } }
                }

                Row { spacing: MichiTheme.spacing.sm; width: parent.width
                    Text { text: qsTr("Disco inicio:"); color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter }
                    SpinBox { id: discStart; from: 1; to: 99; value: 1 }
                        focusPolicy: Qt.StrongFocus
                    MichiButton { text: qsTr("Numerar discos"); variant: "secondary"; onClicked: {
                        if (root.mb) root.mb.batchSetField(root.selectedFiles, "disc_number", String(discStart.value))
                    } }
                }
            }
        }

        MetadataDiffView {
            width: parent.width
        }

        Row {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

            spacing: MichiTheme.spacing.sm
            MichiButton {
                text: root._confirmApply ? "Confirmar aplicar lotes" : qsTr("Aplicar cambios")
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
                text: qsTr("Cancelar")
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
