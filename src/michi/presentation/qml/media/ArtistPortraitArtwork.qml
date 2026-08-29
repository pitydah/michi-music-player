import QtQuick
import QtQuick.Effects
import "../primitives"
import "../theme"

Item {
    id: root

    property string sourcePath: ""
    property string fallbackText: ""
    property int requestedSize: Math.max(width, height)
    property bool selected: false
    property bool hovered: false
    readonly property bool imageReady: portraitSource.status === Image.Ready

    implicitWidth: 120
    implicitHeight: implicitWidth

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: MichiPalette.smokeRaised
        visible: !root.imageReady

        MichiText {
            anchors.centerIn: parent
            text: root.fallbackText.length > 0
                ? root.fallbackText.charAt(0).toUpperCase() : "A"
            role: root.width >= 96 ? "display" : "title"
            font.weight: Font.Medium
            color: MichiPalette.textMuted
        }
    }

    Image {
        id: portraitSource
        anchors.fill: parent
        source: root.sourcePath.length > 0 ? Qt.resolvedUrl(root.sourcePath) : ""
        sourceSize.width: root.requestedSize
        sourceSize.height: root.requestedSize
        asynchronous: true
        cache: true
        fillMode: Image.PreserveAspectCrop
        layer.enabled: true
        visible: false
    }

    Rectangle {
        id: circleMask
        anchors.fill: parent
        radius: width / 2
        color: "white"
        layer.enabled: true
        visible: false
    }

    MultiEffect {
        anchors.fill: parent
        source: portraitSource
        maskEnabled: true
        maskSource: circleMask
        visible: root.imageReady
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: root.selected ? 2 : 1
        border.color: root.selected
            ? MichiSemanticColors.auroraCyanBorderSubtle
            : root.hovered
                ? MichiSemanticColors.borderStrong
                : MichiSemanticColors.borderSubtle

        Behavior on border.color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }
}
