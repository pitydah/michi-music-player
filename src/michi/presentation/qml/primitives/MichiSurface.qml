import QtQuick
import "../theme"

Rectangle {
    id: root
    default property alias contentData: content.data
    property string level: "content"
    property int contentPadding: 0

    color: level === "backplane" ? MichiSemanticColors.backplane
        : level === "control" ? MichiSemanticColors.controlSurface
        : MichiSemanticColors.contentSurface
    radius: level === "backplane" || level === "content" ? 0 : MichiRadius.lg
    border.width: level === "control" ? 1 : 0
    border.color: MichiSemanticColors.borderSubtle

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
    }
}
