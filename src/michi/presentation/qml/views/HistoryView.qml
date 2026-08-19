import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: historyList
    objectName: "historyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.historyRows
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: historyList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.displayName
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
