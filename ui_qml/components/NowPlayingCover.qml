import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string coverKey: ""
    property int coverSize: 56

    implicitWidth: root.coverSize
    implicitHeight: root.coverSize

    CoverImage {
        width: root.coverSize
        height: root.coverSize
        coverRadius: 6
        coverKey: root.coverKey || "NOWPLAYING"
    }
}
