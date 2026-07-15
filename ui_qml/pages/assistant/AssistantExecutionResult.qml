import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string status: "" // success, partial, failure
    property string summaryText: ""
    property string detailText: ""
    property bool detailsExpanded: false
    property bool visible: false
    property string resultStatus: ""
    property var resultDetails: ({})
    property string errorMessage: ""
    property int partialCount: 0
    property int totalCount: 0

    signal retry()
    signal undo()

    implicitHeight: visible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.role: Accessible.Dialog
    Accessible.name: "Resultado de ejecución" + (status === "success" ? " - Éxito" : status === "failure" ? " - Error" : " - Parcial")

    visible: root.visible
    opacity: root.visible ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }

    GlassMaterial {
        radius: MichiTheme.radiusMd
        variant: status === "failure" ? "danger" : status === "partial" ? "warning" : "base"

        Column {
            id: contentColumn
            id: column
    property string status: "" // success, partial, failure
    property string summaryText: ""
    property string detailText: ""
    property bool detailsExpanded: false
    property bool visible: false

    signal retry()
    signal undo()

    implicitHeight: visible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.role: Accessible.Dialog
    Accessible.name: "Resultado de ejecución" + (status === "success" ? " - Éxito" : status === "failure" ? " - Error" : " - Parcial")

    visible: root.visible
    opacity: root.visible ? 1.0 : 0.0
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
                spacing: MichiTheme.spacing.sm
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
                text: resultStatus === "success" ? "La acción se completó correctamente." :
                      resultStatus === "partial" ? partialCount + " de " + totalCount + " acciones completadas." :
                      resultStatus === "failed" ? errorMessage || "Ocurrió un error durante la ejecución." : ""
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
                    objectName: "assistant.result.undo"
                    Accessible.name: "Deshacer cambios"
                    visible: resultStatus === "success" || resultStatus === "partial"
                    onClicked: root.undoTriggered()
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
