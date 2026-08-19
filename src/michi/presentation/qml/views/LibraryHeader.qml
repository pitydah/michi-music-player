import QtQuick
import "../theme"

Text {
    text: "Library" + (library.fileCount > 0 ? " (" + library.fileCount + ")" : "")
    font.pixelSize: MichiTheme.fontSizeBodyLarge
    font.weight: MichiTheme.fontWeightBold
    color: MichiTheme.textSecondary
}
