import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "mixGenerationProgress"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Progreso de generación de mix"

    property int progress: 0
    property int total: 100
    property string statusText: "Generando mix..."
    property bool cancellable: true

    signal cancelRequested()

    implicitHeight: 60

    GlassMaterial {
        anchors.fill: parent; radius: MichiTheme.radiusMd; variant: "subtle"

        Row {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

            MichiProgressBar {
                id: progressBar; width: parent.width - 80; anchors.verticalCenter: parent.verticalCenter
                from: 0; to: root.total; value: root.progress
            }

            Text {
                text: root.statusText; color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "[X]"; color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter; visible: root.cancellable
                objectName: "cancelGenerationBtn"
                Accessible.name: "Cancelar generación"
                Accessible.role: Accessible.Button
                activeFocusOnTab: true
                Keys.onReturnPressed: root.cancelRequested()
                Keys.onSpacePressed: root.cancelRequested()
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: root.cancelRequested()
                }
            }
        }
    }
}
