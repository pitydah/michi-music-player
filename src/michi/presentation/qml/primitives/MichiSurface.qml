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
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop {
            position: 0
            color: root.level === "content"
                ? MichiSemanticColors.contentSurfaceTop : root.color
        }
        GradientStop {
            position: 1
            color: root.level === "content"
                ? MichiSemanticColors.contentSurfaceBottom : root.color
        }
    }
    radius: level === "backplane" || level === "content" ? 0 : MichiRadius.lg
    border.width: level === "control" ? 1 : 0
    border.color: MichiSemanticColors.borderSubtle
    clip: radius > 0

    Rectangle {
        visible: root.level === "content"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.min(150, parent.height * 0.24)
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiSemanticColors.contentAmbientBlue }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    Rectangle {
        visible: root.level === "content"
        anchors.top: parent.top
        anchors.right: parent.right
        width: parent.width * 0.46
        height: Math.min(220, parent.height * 0.34)
        opacity: 0.72
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: MichiSemanticColors.contentAmbientPurple }
        }
    }

    MichiMaterialTexture {
        anchors.fill: parent
        visible: root.level === "content" && opacity > 0
        textureOpacity: MichiThemeState.glassQuality === "high" ? 0.11
            : MichiThemeState.glassQuality === "low" ? 0 : 0.055
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.contentPadding
        z: 1
    }
}
