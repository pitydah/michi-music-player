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
        MichiText {
            anchors.centerIn: parent
            text: root.fallbackText.length > 0 ? root.fallbackText.charAt(0).toUpperCase() : "?"
            role: "title"
            color: MichiPalette.textMuted
        }
    }
    Image {
        id: image
        anchors.fill: parent
        source: root.hasArtwork ? "file://" + root.sourcePath : ""
        sourceSize.width: root.requestedSize
        sourceSize.height: root.requestedSize
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        visible: status === Image.Ready
        opacity: visible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic } }
    }
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: "transparent"
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }
}
