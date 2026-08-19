import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: recentList
    objectName: "recentlyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.recentlyAddedRows
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: recentList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.displayName
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
