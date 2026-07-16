import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Acrylic Backdrop"
    objectName: "acrylicBackdrop"
    focus: true
    id: root

    property string textureHint: "dark"

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
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }
}
