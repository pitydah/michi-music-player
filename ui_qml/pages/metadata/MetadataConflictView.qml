import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mb: null
    property var _conflicts: []

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Conflictos"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Repeater {
                    model: root._conflicts

                    Item {
                        width: parent.width; height: 48
                        Column {
                            anchors.fill: parent; spacing: MichiTheme.spacing.xs
                            Text {
                                text: modelData.field || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                            Text {
                                text: "Valores diferentes entre archivos"
                                color: MichiTheme.colors.warning
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }
                    }
                }

                Text {
                    text: root._conflicts.length === 0 ? "Sin conflictos detectados." : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }
            }
        }
    }
}
