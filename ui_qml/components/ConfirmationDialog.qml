import QtQuick
import "../theme"
import "dialogs"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Confirmation"
    objectName: "confirmationDialog"
    focus: true
    id: root

    property string title: qsTr("Confirmar acción")
    property string message: qsTr("¿Estás seguro?")
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
    property string iconText: ""
    property bool open: false
    property bool destructive: false

    signal confirmed()
    signal cancelled()


    Accessible.description: message

    visible: open

    ConfirmDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        iconType: root.destructive ? "error" : root.iconText ? "warning" : "info"
        open: root.open

        onConfirmed: {
            root.open = false
            root.confirmed()
        }
        onCancelled: {
            root.open = false
            root.cancelled()
        }
    }
}
