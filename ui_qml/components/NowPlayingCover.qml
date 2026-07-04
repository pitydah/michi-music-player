import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string coverKey: ""
    property int coverSize: 56
    property bool placeholderMode: true

    implicitWidth: root.coverSize
    implicitHeight: root.coverSize

    CoverImage {
        width: root.coverSize
        height: root.coverSize
        coverRadius: 6
        coverKey: root.coverKey
        showPlaceholder: root.placeholderMode
    }
}
