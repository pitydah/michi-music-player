import QtQuick
import QtQuick.Layouts
import "../../theme"

Item {
    id: root

    property real leftPeakDbfs: -60
    property real rightPeakDbfs: -60
    property real leftRmsDbfs: -60
    property real rightRmsDbfs: -60
    property bool clippingLeft: false
    property bool clippingRight: false
    property real minimumDbfs: -60
    property real maximumDbfs: 0

    implicitWidth: 150
    implicitHeight: 180
    Accessible.role: Accessible.ProgressBar
    Accessible.name: qsTr("Nivel de entrada estéreo")

    function normalized(dbfs) {
        return Math.max(0, Math.min(1,
            (dbfs - minimumDbfs) / (maximumDbfs - minimumDbfs)))
    }

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Repeater {
            model: [
                {
                    label: "L",
                    peak: root.leftPeakDbfs,
                    rms: root.leftRmsDbfs,
                    clipping: root.clippingLeft
                },
                {
                    label: "R",
                    peak: root.rightPeakDbfs,
                    rms: root.rightRmsDbfs,
                    clipping: root.clippingRight
                }
            ]

            delegate: ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: MichiTheme.spacing.xs

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: MichiTheme.radius.sm
                    color: MichiTheme.colors.surfaceInput
                    border.width: MichiTheme.borderWidth
                    border.color: modelData.clipping
                        ? MichiTheme.colors.error
                        : MichiTheme.colors.borderInner
                    clip: true

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 4
                        height: Math.max(0,
                            (parent.height - 8) * root.normalized(modelData.peak))
                        radius: MichiTheme.radius.xs
                        color: modelData.clipping
                            ? MichiTheme.colors.error
                            : (modelData.peak > -6
                                ? MichiTheme.colors.warning
                                : MichiTheme.colors.success)

                        Behavior on height {
                            NumberAnimation { duration: 70 }
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: Math.max(4,
                            (parent.height - 8) * root.normalized(modelData.rms))
                        anchors.leftMargin: 3
                        anchors.rightMargin: 3
                        height: 2
                        color: MichiTheme.colors.textPrimary
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: modelData.label
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Number(modelData.peak).toFixed(1) + " dB"
                    color: modelData.clipping
                        ? MichiTheme.colors.error
                        : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }
}
