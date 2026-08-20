import QtQuick
import "../theme"

Rectangle {
    id: root
    default property alias contentData: content.data
    property string elevation: "standard"
    property int contentPadding: MichiSpacing.lg
    readonly property real materialOpacity: MichiThemeState.glassQuality === "low" ? 0.96
        : MichiThemeState.glassQuality === "high" ? 0.76 : 0.86

    color: elevation === "modal" || elevation === "elevated"
        ? Qt.rgba(0.075, 0.09, 0.125, Math.min(1, root.materialOpacity + 0.04))
        : Qt.rgba(0.065, 0.078, 0.11, root.materialOpacity)
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
