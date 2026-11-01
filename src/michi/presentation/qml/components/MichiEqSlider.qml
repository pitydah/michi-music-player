import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// F11 vertical EQ rail. Draft-only: the owner commits on release.
Item {
    id: root
    property real gainDb: 0
    property string bandLabel: ""
    property bool inactive: false
    property string inactiveReason: ""
    signal gainCommitted(real gain)

    implicitWidth: 34
    implicitHeight: 172

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xs

        MichiText {
            text: root.gainDb > 0 ? "+" + root.gainDb.toFixed(1)
                : root.gainDb.toFixed(1)
            role: "micro"
            color: root.inactive ? MichiPalette.textDisabled
                : root.gainDb === 0 ? MichiPalette.textMuted
                : MichiPalette.textPrimary
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            font.weight: Font.DemiBold
        }

        Slider {
            id: slider
            orientation: Qt.Vertical
            from: -12
            to: 12
            stepSize: 0.5
            value: root.gainDb
            enabled: !root.inactive
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 34
            Layout.fillHeight: true
            Accessible.role: Accessible.Slider
            Accessible.name: qsTr("%1 Hz equalizer band").arg(root.bandLabel)
            Accessible.description: root.inactive
                ? root.inactiveReason
                : qsTr("%1 decibels").arg(root.gainDb.toFixed(1))

            onMoved: root.gainDb = value
            onPressedChanged: {
                if (!pressed)
                    root.gainCommitted(value)
            }

            background: Rectangle {
                x: (slider.availableWidth - width) / 2
                y: (slider.availableHeight - height) / 2
                width: 6
                height: Math.min(125, slider.availableHeight)
                radius: MichiRadius.pill
                color: MichiPalette.smokeRaised
                opacity: root.inactive ? 0.45 : 1

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: Math.max(2, parent.height * slider.visualPosition)
                    radius: MichiRadius.pill
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0; color: MichiPalette.auroraCyan }
                        GradientStop { position: 0.28; color: MichiPalette.auroraBlue }
                        GradientStop { position: 1; color: MichiPalette.auroraBlue }
                    }
                    opacity: root.inactive ? 0.35 : 1
                }
            }

            handle: Rectangle {
                x: (slider.availableWidth - width) / 2
                y: slider.topPadding
                    + (slider.availableHeight - height) * (1 - slider.visualPosition)
                width: 14
                height: 14
                radius: width / 2
                color: root.inactive ? MichiPalette.textDisabled : MichiPalette.textPrimary
                border.width: 2
                border.color: slider.pressed || slider.visualFocus
                    ? MichiPalette.auroraCyan
                    : slider.hovered ? MichiPalette.auroraBlue
                    : MichiPalette.auroraPurple
                scale: slider.pressed ? 1.08 : slider.hovered ? 1.04 : 1
                Behavior on scale {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.micro
                        easing.type: MichiMotion.outCubic
                    }
                }
                MichiFocusRing { visualFocus: slider.visualFocus }
            }
        }

        MichiText {
            text: root.bandLabel
            role: "micro"
            color: root.inactive ? MichiPalette.textDisabled
                : MichiPalette.textSecondary
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
    }

    MichiTooltip {
        visible: root.inactive && hoverArea.hovered
        text: root.inactiveReason
    }
    HoverHandler { id: hoverArea }
}
