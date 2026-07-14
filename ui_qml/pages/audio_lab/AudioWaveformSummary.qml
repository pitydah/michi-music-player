import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var waveformData: null

    visible: root.waveformData !== null

    GlassMaterial {
        width: parent.width; height: 100; radius: MichiTheme.radiusSm; variant: "base"
        Text {
            anchors.centerIn: parent
            text: root.waveformData ? "Resumen de forma de onda disponible" : "Sin datos de forma de onda"
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; color: "transparent"
            visible: root.waveformData !== null
        }
    }
}
