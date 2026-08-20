import QtQuick
import "../theme"

Rectangle {
    id: root
    default property alias contentData: content.data
    property string elevation: "standard"
    property int contentPadding: MichiSpacing.lg
    property bool accented: false
    property color accentColor: MichiPalette.auroraBlue
    readonly property real materialOpacity: MichiThemeState.glassQuality === "low" ? 0.96
        : MichiThemeState.glassQuality === "high" ? 0.76 : 0.86
    readonly property color materialTop: elevation === "modal" || elevation === "elevated"
        ? Qt.rgba(0.086, 0.102, 0.142, Math.min(1, root.materialOpacity + 0.05))
        : Qt.rgba(0.073, 0.087, 0.12, Math.min(1, root.materialOpacity + 0.02))
    readonly property color materialBottom: elevation === "modal" || elevation === "elevated"
        ? Qt.rgba(0.052, 0.062, 0.088, Math.min(1, root.materialOpacity + 0.08))
        : Qt.rgba(0.049, 0.059, 0.083, root.materialOpacity)

    color: root.materialBottom
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop { position: 0; color: root.materialTop }
        GradientStop { position: 1; color: root.materialBottom }
    }
    radius: elevation === "subtle" ? MichiRadius.md : MichiRadius.floating
    border.width: 1
    border.color: MichiAccessibility.highContrast
        ? MichiSemanticColors.borderStrong
        : root.accented ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.22)
        : MichiSemanticColors.borderSubtle

    Rectangle {
        visible: root.accented
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: 1
        color: root.accentColor
        opacity: MichiAccessibility.highContrast ? 0.9 : 0.42
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        radius: root.radius
        color: MichiSemanticColors.innerHighlight
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: 1
        color: Qt.rgba(0, 0, 0, 0.22)
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
    }
}
