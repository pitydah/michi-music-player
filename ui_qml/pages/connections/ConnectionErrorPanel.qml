import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string errorText: ""
    property string objectName: "connectionErrorPanel"

    signal retryClicked()
    signal dismissClicked()

    implicitHeight: childrenRect.height

    Accessible.role: Accessible.Alert
    Accessible.name: "Error de conexión"
    Accessible.description: root.errorText

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "accent"
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
                    color: MichiTheme.colors.statusError
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: root.objectName + ".title"
                }
            }

            Text {
                text: root.errorText
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
                objectName: root.objectName + ".message"
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Reintentar"
                    variant: "primary"
                    onClicked: root.retryClicked()
                    objectName: root.objectName + ".retryButton"
                    Accessible.name: "Reintentar conexión"
                }

                MichiButton {
                    text: "Descartar"
                    variant: "ghost"
                    onClicked: root.dismissClicked()
                    objectName: root.objectName + ".dismissButton"
                    Accessible.name: "Descartar error"
                }
            }
        }
    }
}
