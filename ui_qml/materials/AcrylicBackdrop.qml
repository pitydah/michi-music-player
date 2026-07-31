import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Fondo acrílico")
    objectName: "acrylicBackdrop"
    id: root

    property string textureHint: "dark"
    property bool textured: true

    Rectangle {
        anchors.fill: parent
        color: {
            switch (root.textureHint) {
                case "hero": return MichiTheme.colors.surfaceHero
                default: return MichiTheme.colors.bgApp
            }
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.accentSurface }
                GradientStop { position: 0.38; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.0) }
                GradientStop { position: 1.0; color: MichiTheme.colors.shadowSoft }
            }
        }

        TextureOverlay {
            anchors.fill: parent
            variant: root.textureHint === "hero" ? "contours" : "grain"
            strength: root.textureHint === "hero" ? 0.72 : 0.46
            visible: root.textured
        }
    }
}
