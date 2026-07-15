import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string resultStatus: ""
    property var resultDetails: ({})
    property string errorMessage: ""
    property int partialCount: 0
    property int totalCount: 0

    signal retryTriggered()
    signal undoTriggered()

    Accessible.role: Accessible.Panel
    Accessible.name: "Resultado de ejecución"

    implicitHeight: column.height + MichiTheme.spacing.lg * 2
    visible: resultStatus !== ""

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        variant: resultStatus === "success" ? "accent" : resultStatus === "partial" ? "status" : "base"
        border.color: resultStatus === "failed" ? MichiTheme.colors.error : MichiTheme.colors.borderCard

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: resultStatus === "success" ? "Completado" :
                          resultStatus === "partial" ? "Completado parcialmente" :
                          resultStatus === "failed" ? "Error" : resultStatus
                    color: resultStatus === "success" ? MichiTheme.colors.success :
                           resultStatus === "failed" ? MichiTheme.colors.error :
                           MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
            }

            Text {
                text: resultStatus === "success" ? "La acción se completó correctamente." :
                      resultStatus === "partial" ? partialCount + " de " + totalCount + " acciones completadas." :
                      resultStatus === "failed" ? errorMessage || "Ocurrió un error durante la ejecución." : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Rectangle {
                visible: resultDetails && Object.keys(resultDetails).length > 0
                width: parent.width
                height: detailsColumn.height + MichiTheme.spacing.sm
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surfaceInput

                Column {
                    id: detailsColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: resultDetails ? Object.keys(resultDetails) : []

                        Row {
                            width: parent.width
                            spacing: MichiTheme.spacing.xs
                            Text {
                                text: modelData + ":"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.35
                                elide: Text.ElideRight
                            }
                            Text {
                                text: resultDetails[modelData] || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.60
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                layoutDirection: Qt.RightToLeft

                MichiButton {
                    text: "Reintentar"
                    variant: "secondary"
                    objectName: "assistant.result.retry"
                    Accessible.name: "Reintentar acción"
                    visible: resultStatus === "failed" || resultStatus === "partial"
                    onClicked: root.retryTriggered()
                }

                MichiButton {
                    text: "Deshacer"
                    variant: "ghost"
                    objectName: "assistant.result.undo"
                    Accessible.name: "Deshacer cambios"
                    visible: resultStatus === "success" || resultStatus === "partial"
                    onClicked: root.undoTriggered()
                }
            }
        }
    }
}
