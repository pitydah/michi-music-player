import QtQuick
import "../theme"

Rectangle {
    id: root

    default property alias content: contentArea.data

    color: MichiTheme.surfacePrimary
    radius: MichiTheme.radiusLarge
    border.color: MichiTheme.borderSubtle
    border.width: 1

    Item {
        id: contentArea
        anchors.fill: parent
        anchors.margins: MichiTheme.space16
    }
}
