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
    readonly property bool raised: elevation === "modal" || elevation === "elevated"
    readonly property color materialTop: MichiSemanticColors.glassTop(
        root.raised, root.materialOpacity)
    readonly property color materialBottom: MichiSemanticColors.glassBottom(
        root.raised, root.materialOpacity)

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
        : root.accented ? MichiSemanticColors.accentBorder(root.accentColor)
        : root.raised ? MichiSemanticColors.borderStrong
        : MichiSemanticColors.borderSubtle

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        color: "transparent"
        border.width: 1
        border.color: MichiSemanticColors.glassInnerBorder
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 1
        anchors.rightMargin: 1
        anchors.topMargin: 1
        height: Math.min(parent.height * 0.42, 36)
        radius: Math.max(0, root.radius - 1)
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiSemanticColors.glassSheen }
            GradientStop { position: 1; color: "transparent" }
        }
    }

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
        color: MichiSemanticColors.glassShadow
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
    }
}
