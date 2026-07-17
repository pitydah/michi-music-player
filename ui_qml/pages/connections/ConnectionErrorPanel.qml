import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Connection Error"
    objectName: "connectionErrorPanel"
    focus: true
    id: root

    property string errorText: ""

    signal retryClicked()
    signal dismissClicked()

    implicitHeight: childrenRect.height

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radius.md
        variant: "primary"
        visible: root.errorText !== ""

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Error de conexión"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
            }

            Text {
                text: root.errorText
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Reintentar"
                    variant: "primary"
                    onClicked: root.retryClicked()
                }

                MichiButton {
                    text: "Descartar"
                    variant: "ghost"
                    onClicked: root.dismissClicked()
                }
            }
        }
    }
}
