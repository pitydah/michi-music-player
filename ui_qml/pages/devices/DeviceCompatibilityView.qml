import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Compatibility View"
    objectName: "deviceCompatibilityView"
    focus: true
    id: root

    property string protocol: ""
    property var supportedFormats: [".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac", ".wma", ".dsf", ".dff", ".ape", ".aiff"]
    property var unsupportedFormats: [".wmv", ".avi", ".mkv", ".mp4"]

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
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Compatibilidad de formatos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Protocolo: " + (root.protocol || "Desconocido")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Text {
                text: "Formatos soportados"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.supportedFormats
                    StatusBadge {
                        text: modelData; kind: "success"
                    }
                }
            }

            Text {
                text: "Formatos no soportados (solo audio)"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.unsupportedFormats
                    StatusBadge {
                        text: modelData; kind: "disconnected"
                    }
                }
            }
        }
    }
}
