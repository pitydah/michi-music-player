import QtQuick
import "../theme"

Rectangle {
    id: root
    default property alias contentData: content.data
    property string elevation: "standard"
    property int contentPadding: MichiSpacing.lg

    color: elevation === "modal" || elevation === "elevated"
        ? MichiSemanticColors.controlSurfaceStrong
        : MichiSemanticColors.controlSurface
    radius: elevation === "subtle" ? MichiRadius.md : MichiRadius.floating
    border.width: 1
    border.color: MichiAccessibility.highContrast
        ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        radius: root.radius
        color: MichiSemanticColors.innerHighlight
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
    }
}
