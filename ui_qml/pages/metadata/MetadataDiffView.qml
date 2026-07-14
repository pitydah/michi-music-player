import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mb: null
    property var _diffs: []

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Diferencias"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Repeater {
                    model: root._diffs

                    Item {
                        width: parent.width; height: 28
                        Row {
                            anchors.fill: parent; spacing: MichiTheme.spacing.sm
                            Text {
                                width: parent.width * 0.30
                                text: modelData.field || ""
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Text {
                                width: parent.width * 0.30
                                text: modelData.oldValue || "—"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Text {
                                width: parent.width * 0.30
                                text: "→ " + (modelData.newValue || "")
                                color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }

                Text {
                    text: root._diffs.length === 0 ? "Sin cambios para mostrar." : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }
            }
        }
    }
}
