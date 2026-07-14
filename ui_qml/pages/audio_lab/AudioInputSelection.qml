import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var selCtx: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property var libBridge: typeof libraryBridge !== "undefined" ? libraryBridge : null

    signal filesSelected(var filepaths)

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        Text {
            text: "Selección de entrada"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
        }

        Row {
            spacing: MichiTheme.spacing.sm
            MichiButton {
                text: "Desde biblioteca"
                variant: "secondary"
                onClicked: {
                    if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("library")
                }
            }
            MichiButton {
                text: "Seleccionar archivos"
                variant: "secondary"
                onClicked: {
                    if (root.libBridge && root.libBridge.selectFiles)
                        root.libBridge.selectFiles()
                }
            }
            MichiButton {
                text: "Pegar ruta"
                variant: "ghost"
            }
        }

        Text {
            text: "Origen compatible: library table, álbum, artista, carpeta, playlist, búsqueda, Mix, drag-drop, archivos externos, multi-selección, dispositivos"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
            width: parent.width
        }
    }
}
