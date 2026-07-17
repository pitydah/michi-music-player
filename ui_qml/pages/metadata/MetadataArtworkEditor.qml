import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Artwork Editor"
    objectName: "metadataArtworkEditor"
    focus: true
    id: root

    property var mb: null
    property bool _confirmRemove: false

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Carátula"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                MetadataArtworkPreview {
                    width: parent.width
                    artworkStatus: root.mb ? root.mb.artworkStatus : ""
                    coverKey: root.mb && root.mb.hasSelection ? "editor" : ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                        text: "Elegir archivo"
                        variant: "secondary"
                        onClicked: artworkFileDialog.open()
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                    }
                    MichiButton {
                        text: "Extraer carátula"
                        variant: "ghost"
                        onClicked: {
                            if (root.mb && typeof root.mb.hasArtwork !== "undefined")
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                                root.mb.hasArtwork()
                        }
                    }
                    MichiButton {
                        text: root._confirmRemove ? "Confirmar eliminar" : "Eliminar carátula"
                        variant: root._confirmRemove ? "danger" : "ghost"
                        onClicked: {
                            if (!root._confirmRemove) {
                                root._confirmRemove = true
                            } else {
                                root._confirmRemove = false
                                if (root.mb && typeof root.mb.removeArtwork !== "undefined")
                                    root.mb.removeArtwork()
                            }
                        }
                    }
                }

                Text {
                    text: root.mb ? root.mb.artworkStatus : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }
            }
        }

        FileDialog {
            id: artworkFileDialog
            title: "Seleccionar imagen de carátula"
            nameFilters: ["Imágenes (*.png *.jpg *.jpeg *.webp)", "Todos los archivos (*)"]
            onAccepted: {
                var path = artworkFileDialog.selectedFile.toString().replace("file://", "")
                if (root.mb && typeof root.mb.replaceArtwork !== "undefined")
                    root.mb.replaceArtwork(path)
            }
        }
    }
}
