import QtQuick
import "../theme"

Item {
    id: root
    property bool selected: false
    property color labelColor: selected ? MichiPalette.auroraCyan : MichiPalette.graphite

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        border.width: 1
        border.color: MichiSemanticColors.borderStrong
        gradient: Gradient {
            GradientStop { position: 0; color: MichiPalette.vinylOuter }
            GradientStop { position: 0.46; color: MichiPalette.vinylMid }
            GradientStop { position: 1; color: MichiPalette.vinylInner }
        }
    }

    Repeater {
        model: 5
        Rectangle {
            required property int index
            anchors.centerIn: parent
            width: root.width * (0.9 - index * 0.13)
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: index % 2 === 0
                ? MichiSemanticColors.borderSubtle : MichiSemanticColors.innerHighlight
            opacity: 0.42
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 0.32
        height: width
        radius: width / 2
        color: root.labelColor
        border.width: 1
        border.color: MichiSemanticColors.innerHighlight
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.selection }
        }
        Rectangle {
            anchors.centerIn: parent
            width: MichiSpacing.xs
            height: width
            radius: width / 2
            color: MichiPalette.obsidian
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: MichiSemanticColors.innerHighlight
        opacity: 0.35
    }
}
