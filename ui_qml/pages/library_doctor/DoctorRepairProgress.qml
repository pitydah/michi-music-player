import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var doc: null
    property int progress: 0
    property int total: 0
    property string currentOperation: ""
    property bool _cancelling: false

    signal cancelRequested()
    signal retryFailed()

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        GlassMaterial {
            width: parent.width
            radius: MichiTheme.radiusMd
            variant: "danger"
            visible: root.total > 0

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Reparando problemas..."
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                MichiProgressBar {
                    width: parent.width
                    value: root.total > 0 ? root.progress / root.total * 100 : 0
                    indeterminate: root.total === 0
                }

                Text {
                    text: root.currentOperation !== ""
                          ? root.currentOperation
                          : (root.total > 0 ? root.progress + " / " + root.total : "Inicializando...")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                StatusBadge {
                    text: root._cancelling ? "Cancelando..." : "Reparación en curso"
                    kind: "warning"
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        text: root._cancelling ? "Cancelando..." : "Cancelar"
                        variant: "ghost"
                        enabled: !root._cancelling
                        objectName: "doctorCancelRepairProgressButton"
                        Accessible.name: "Cancelar reparación en curso"
                        onClicked: {
                            root._cancelling = true
                            root.cancelRequested()
                        }
                    }

                    MichiButton {
                        text: "Reintentar fallidos"
                        variant: "primary"
                        enabled: false
                        objectName: "doctorRetryFailedButton"
                        Accessible.name: "Reintentar reparaciones fallidas"
                        visible: false
                        onClicked: root.retryFailed()
                    }
                }
            }
        }
    }

    function reset() {
        root.progress = 0
        root.total = 0
        root.currentOperation = ""
        root._cancelling = false
    }
}
