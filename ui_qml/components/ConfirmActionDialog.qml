import QtQuick
import "../theme"
import "dialogs"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Confirm Action"
    objectName: "confirmActionDialog"
    focus: true
    id: root

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro?"
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
    property bool danger: false
    property bool open: false

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
        iconType: root.danger ? "error" : "info"
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
