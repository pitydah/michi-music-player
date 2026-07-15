import QtQuick
import QtQuick.Controls
import "../../theme"

Item {
    id: root
    width: 20; height: 20

    property bool favorite: false
    property bool missing: false

    Text {
        anchors.centerIn: parent
        text: root.favorite ? "★" : root.missing ? "[X]" : ""
        color: root.favorite ? MichiTheme.colors.warning : root.missing ? MichiTheme.colors.error : "transparent"
        font.pixelSize: 12
        visible: root.favorite || root.missing
    }
}
