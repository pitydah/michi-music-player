import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: favoritesList
    objectName: "favoritesView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.favoriteRows
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: favoritesList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.displayName
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
