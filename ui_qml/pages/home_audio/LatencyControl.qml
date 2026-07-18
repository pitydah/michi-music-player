import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Latency Control"
    objectName: "latencyControl"
    focus: true
    id: root

    property int currentLatencyMs: 0
    property int minLatency: 0
    property int maxLatency: 500

    signal latencyChanged(int ms)

    implicitHeight: childrenRect.height

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radius.md
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: qsTr("Control de latencia")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Latencia actual: ") + root.currentLatencyMs + " ms"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            MichiSlider {
                Accessible.role: Accessible.Slider

                id: latencySlider
                activeFocusOnTab: true

                width: parent.width
                from: root.minLatency
                to: root.maxLatency
                value: root.currentLatencyMs
                stepSize: 5

                onMoved: {
                    root.currentLatencyMs = value
                    root.latencyChanged(value)
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text { text: root.minLatency + " ms"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                Item { width: parent.width - 100; height: 1 }
                Text { text: root.maxLatency + " ms"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            }
        }
    }
}
