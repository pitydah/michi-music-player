import QtQuick
import "../theme"
import "../components"

Item {
    id: root

    property string title: ""
    property string jobId: ""
    property int progress: 0
    property bool indeterminate: false
    property bool cancellable: true
    property string objectName: "notificationProgressItem"

    signal cancelRequested(string jobId)
    signal dismissRequested(string jobId)

    implicitHeight: 80
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title + ". " + root.progress + "%"
    Accessible.description: root.indeterminate ? "Progreso indeterminado" : root.progress + "% completado"

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: MichiTheme.colors.surfaceCard
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    width: parent.width - 80
                }

                Text {
                    text: !root.indeterminate ? root.progress + "%" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !root.indeterminate
                }
            }

            MichiProgressBar {
                width: parent.width
                value: root.progress
                indeterminate: root.indeterminate
                accessibleName: root.Accessible.name
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.cancellable

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.cancelRequested(root.jobId)
                }

                MichiButton {
                    text: "Descartar"
                    variant: "ghost"
                    onClicked: root.dismissRequested(root.jobId)
                }
            }
        }
    }
}
