import QtQuick
import "../theme"
import "dialogs"

Item {
    id: root

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro?"
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
    property string iconText: ""
    property bool open: false
    property bool destructive: false

    signal confirmed()
    signal cancelled()

    objectName: "ConfirmationDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
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
