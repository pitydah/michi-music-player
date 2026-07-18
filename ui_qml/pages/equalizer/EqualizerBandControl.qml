import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Equalizer Band Control"
    objectName: "equalizerBandControl"
    focus: true
    id: root

    property real freq: 0
    property real gain: 0
    property int index: 0
    property bool eqEnabled: true

    signal bandGainChanged(int idx, real val)

    implicitHeight: 48

    Row {
        spacing: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter

        Text {
            text: root.freq >= 1000
                ? (root.freq / 1000).toFixed(0) + " kHz"
                : root.freq.toFixed(0) + " Hz"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            width: 70
            anchors.verticalCenter: parent.verticalCenter
        }

        MichiSlider {
            Accessible.role: Accessible.Slider

            activeFocusOnTab: true

            width: 200
            from: -24; to: 24; value: root.gain
            stepSize: 0.5
            enabled: root.enabled && root.eqEnabled
            accessibleName: "Banda " + root.freq + " Hz"
            onMoved: root.bandGainChanged(root.index, value)
        }

        Text {
            text: root.gain.toFixed(1) + " dB"
            color: root.gain >= 0 ? MichiTheme.colors.accentBlue : MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            width: 60
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: qsTr("No disponible con este backend")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            anchors.verticalCenter: parent.verticalCenter
            visible: !root.enabled || !root.eqEnabled
        }
    }
}
