import QtQuick
import QtQuick.Controls.Basic
import "../controls"

MichiMenu {
    id: root
    property var genre: null
    MenuItem {
        text: qsTr("Open Genre")
        icon.name: "genre"
        visible: root.genre !== null
        onTriggered: library.select_genre(root.genre.key)
    }
}
