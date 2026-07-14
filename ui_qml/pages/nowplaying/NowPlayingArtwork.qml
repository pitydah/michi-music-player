import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    property string coverKey: ""
    property bool placeholderMode: true

    implicitWidth: 240
    implicitHeight: 240

    CoverImage {
        anchors.fill: parent
        coverRadius: MichiTheme.radius.lg
        coverKey: root.coverKey
        showPlaceholder: root.placeholderMode
    }
}
