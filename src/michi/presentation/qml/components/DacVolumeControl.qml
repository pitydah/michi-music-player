import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

RowLayout {
    id: root
    spacing: MichiSpacing.xs

    property int volume: 100
    property bool muted: false
    property bool volumeAdjustable: true
    property string volumeMode: "michi_software"
    property string volumeModeLabel: qsTr("Software volume")

    signal volumeChangeRequested(int value)
    signal muteToggleRequested(bool muted)

    MichiIconButton {
        objectName: "muteButton"
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        iconName: root.muted || root.volume === 0 ? "mute" : "volume"
        accessibleName: root.muted ? qsTr("Unmute") : qsTr("Mute")
        onClicked: root.muteToggleRequested(!root.muted)
    }

    Slider {
        id: volumeSlider
        objectName: "volumeSlider"
        Layout.fillWidth: true
        Layout.minimumWidth: 72
        Layout.preferredHeight: 28
        from: 0
        to: 100
        value: root.volume
        enabled: root.volumeAdjustable
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        Accessible.role: Accessible.Slider
        Accessible.name: root.volumeAdjustable
            ? qsTr("Volume") : qsTr("Fixed / Unity")
        Accessible.description: root.volumeAdjustable
            ? qsTr("%1 percent").arg(Math.round(value))
            : root.volumeModeLabel
        onMoved: root.volumeChangeRequested(Math.round(value))

        background: Rectangle {
            x: volumeSlider.leftPadding
            y: volumeSlider.topPadding
                + volumeSlider.availableHeight / 2 - height / 2
            width: volumeSlider.availableWidth
            height: 6
            radius: height / 2
            color: MichiPalette.smokeRaised
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle

            Rectangle {
                width: volumeSlider.visualPosition * parent.width
                height: parent.height
                radius: parent.radius
                color: root.volumeAdjustable
                    ? MichiPalette.auroraBlue : MichiPalette.textDisabled
            }
        }

        handle: Rectangle {
            x: volumeSlider.leftPadding + volumeSlider.visualPosition
                * (volumeSlider.availableWidth - width)
            y: volumeSlider.topPadding
                + volumeSlider.availableHeight / 2 - height / 2
            width: 14
            height: 14
            radius: 7
            color: root.volumeAdjustable
                ? MichiPalette.textPrimary : MichiPalette.textDisabled
            border.width: 2
            border.color: volumeSlider.visualFocus || volumeSlider.hovered
                ? MichiPalette.auroraCyan : MichiPalette.auroraPurple
            scale: volumeSlider.pressed ? 1.08
                : volumeSlider.hovered ? 1.04 : 1

            Behavior on scale {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation {
                    duration: MichiMotion.micro
                    easing.type: MichiMotion.outCubic
                }
            }

            MichiFocusRing { visualFocus: volumeSlider.visualFocus }
        }
    }

    MichiText {
        Layout.preferredWidth: root.volumeAdjustable ? 34 : 82
        text: root.volumeAdjustable
            ? qsTr("%1%").arg(Math.round(root.volume))
            : root.volumeModeLabel
        role: "technical"
        technical: true
        color: root.volumeAdjustable
            ? MichiPalette.textMuted : MichiPalette.auroraCyan
        horizontalAlignment: Text.AlignRight
    }
}
