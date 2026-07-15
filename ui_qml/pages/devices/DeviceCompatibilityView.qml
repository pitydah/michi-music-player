import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string protocol: ""
    property var supportedFormats: [".mp3", ".flac", ".wav", ".ogg", ".opus", ".m4a", ".aac", ".wma", ".dsf", ".dff", ".ape", ".aiff"]
    property var unsupportedFormats: [".wmv", ".avi", ".mkv", ".mp4"]

    implicitHeight: childrenRect.height

    objectName: "DeviceCompatibilityView"
    Accessible.role: Accessible.Pane
    Accessible.name: "Compatibilidad de formatos"

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
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
                objectName: "compatibilityTitle"
                Accessible.name: "Compatibilidad de formatos"
            }

            Text {
                text: "Protocolo: " + (root.protocol || "Desconocido")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                objectName: "compatibilityProtocol"
                Accessible.name: text
            }

            Text {
                text: "Formatos soportados"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                objectName: "supportedFormatsTitle"
                Accessible.name: "Formatos soportados"
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.supportedFormats
                    StatusBadge {
                        text: modelData; kind: "success"
                        objectName: "supportedFormat_" + index
                        Accessible.name: modelData
                    }
                }
            }

            Text {
                text: "Formatos no soportados (solo audio)"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                objectName: "unsupportedFormatsTitle"
                Accessible.name: "Formatos no soportados — solo audio"
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.xs

                Repeater {
                    model: root.unsupportedFormats
                    StatusBadge {
                        text: modelData; kind: "disconnected"
                        objectName: "unsupportedFormat_" + index
                        Accessible.name: modelData + " no soportado"
                    }
                }
            }
        }
    }
}
