import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Assistant Execution Result"
    objectName: "assistantExecutionResult"
    focus: true
    id: root

    property string status: "" // success, partial, failure
    property string summaryText: ""
    property string detailText: ""
    property bool detailsExpanded: false
    property bool resultVisible: false

    signal retry()
    signal undo()

    implicitHeight: resultVisible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.role: Accessible.Dialog
    Accessible.name: "Resultado de ejecución" + (status === "success" ? " - Éxito" : status === "failure" ? " - Error" : " - Parcial")

    visible: root.resultVisible
    opacity: root.resultVisible ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }

    GlassMaterial {
        radius: MichiTheme.radiusMd
        variant: status === "failure" ? "danger" : status === "partial" ? "warning" : "base"

        Column {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: status === "success" ? "✓" : status === "partial" ? "⚠" : "✗"
                    color: status === "success" ? MichiTheme.colors.success : status === "partial" ? MichiTheme.colors.warning : MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: status === "success" ? "Completado" : status === "partial" ? "Completado parcialmente" : "Error"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                width: parent.width
                text: root.summaryText
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Rectangle {
                width: parent.width
                height: 28
                radius: MichiTheme.radiusXs
                color: MichiTheme.colors.surfaceSubtle
                visible: root.detailText !== ""

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.detailsExpanded = !root.detailsExpanded
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.spacing.sm
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.detailsExpanded ? "Ocultar detalles" : "Ver detalles"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightMedium
                }
            }

            Text {
                width: parent.width
                text: root.detailText
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                visible: root.detailsExpanded && root.detailText !== ""
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                layoutDirection: Qt.RightToLeft

                MichiButton {
                    text: status === "failure" ? "Reintentar" : "Deshacer"
                    variant: status === "failure" ? "primary" : "ghost"
                    visible: (status === "failure" || status === "partial")
                    objectName: "executionResultRetry"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: {
                        if (status === "failure") root.retry()
                        else root.undo()
                    }
                }

                MichiButton {
                    text: "Cerrar"
                    variant: "ghost"
                    objectName: "executionResultClose"
                    Accessible.name: "Cerrar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.visible = false
                }
            }
        }
    }
}
