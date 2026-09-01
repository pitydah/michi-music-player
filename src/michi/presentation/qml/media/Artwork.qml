import QtQuick
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property string sourcePath: ""
    property string fallbackText: "?"
    property int requestedSize: Math.max(width, height)
    property bool rounded: true
    readonly property bool hasArtwork: sourcePath.length > 0
    readonly property bool failed: image.status === Image.Error
    color: MichiPalette.smoke
    radius: rounded ? MichiRadius.md : 0
    clip: true

    Rectangle {
        anchors.fill: parent
        color: MichiPalette.smokeRaised
        visible: !root.hasArtwork || root.failed
        MichiIcon {
            anchors.centerIn: parent
            width: Math.min(parent.width * 0.5, 20)
            height: width
            name: "album"
            iconColor: MichiPalette.textMuted
            visible: root.fallbackText === "?" || root.fallbackText === ""
        }
        MichiText {
            anchors.centerIn: parent
            text: root.fallbackText.length > 0 ? root.fallbackText.charAt(0).toUpperCase() : ""
            role: root.width > 48 ? "title" : "caption"
            font.weight: Font.DemiBold
            color: MichiPalette.textMuted
            visible: root.fallbackText !== "?" && root.fallbackText !== ""
        }
    }
    Image {
        id: image
        anchors.fill: parent
        // Qt resolves absolute local paths and already-normalized URLs;
        // callers never concatenate or strip file:// prefixes themselves.
        source: root.hasArtwork ? Qt.resolvedUrl(root.sourcePath) : ""
        sourceSize.width: root.requestedSize
        sourceSize.height: root.requestedSize
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        visible: status === Image.Ready
        opacity: visible ? 1 : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
        }
    }
    // Physical spine shadow on the left edge
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        visible: root.hasArtwork && image.status === Image.Ready
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: MichiSemanticColors.glassShadow }
            GradientStop { position: 1; color: "transparent" }
        }
        z: 2
    }

    // Top physical rim highlight
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        visible: root.hasArtwork && image.status === Image.Ready
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: MichiSemanticColors.innerHighlight }
            GradientStop { position: 0.8; color: MichiSemanticColors.glassInnerBorder }
            GradientStop { position: 1; color: "transparent" }
        }
        z: 2
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
        z: 3
    }
}
