import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Equalizer Graph"
    objectName: "equalizerGraph"
    focus: true
    id: root

    property var eqBridge: null
    property real _maxGain: 24
    property real _bandWidth: width / Math.max(1, bandCount)
    property int bandCount: root.eqBridge ? root.eqBridge.graphicBands.length : 10

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCard

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xxs

            Repeater {
                model: root.eqBridge ? root.eqBridge.graphicBands : []

                Item {
                    width: root._bandWidth - 2
                    height: parent.height

                    property real gain: modelData ? modelData.gain : 0
                    property real freq: modelData ? modelData.freq : 0
                    property real barHeight: Math.abs(gain) / root._maxGain * (parent.height * 0.7)
                    property real barY: gain >= 0
                        ? parent.height * 0.85 - barHeight
                        : parent.height * 0.85

                    Rectangle {
                        x: 2; width: parent.width - 4
                        y: root.gain >= 0 ? barY : parent.height * 0.85
                        height: Math.max(2, root.barHeight)
                        radius: MichiTheme.radius.xs
                        color: root.gain >= 0
                            ? (root.gain > 6 ? MichiTheme.colors.warning : MichiTheme.colors.accentBlue)
                            : MichiTheme.colors.error
                        opacity: MichiTheme.opacity.hover
                    }

                    Rectangle {
                        anchors.left: parent.left; anchors.right: parent.right
                        y: parent.height * 0.85
                        height: 1
                        color: MichiTheme.colors.borderSubtle
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: parent.height - MichiTheme.spacing.sm
                        text: root.freq >= 1000
                            ? (root.freq / 1000).toFixed(0) + "k"
                            : root.freq.toFixed(0)
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: MichiTheme.spacing.xxs
                        text: root.gain.toFixed(1)
                        color: root.gain >= 0 ? MichiTheme.colors.accentBlue : MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }
            }
        }
    }
}
