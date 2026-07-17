import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Doctor Repair Progress"
    objectName: "doctorRepairProgress"
    focus: true
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
            radius: MichiTheme.radius.md
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
                    Accessible.role: Accessible.ProgressBar

                    activeFocusOnTab: true

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
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true


                    MichiButton {
                        text: root._cancelling ? "Cancelando..." : "Cancelar"
                        variant: "ghost"
                        enabled: !root._cancelling
                        onClicked: {
                            root._cancelling = true
                            root.cancelRequested()
                        Accessible.role: Accessible.Button

                        activeFocusOnTab: true

                        }
                    }

                    MichiButton {
                        text: "Reintentar fallidos"
                        variant: "primary"
                        enabled: false
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
