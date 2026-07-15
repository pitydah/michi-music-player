import QtQuick
import "../theme"
import "dialogs"

Item {
    id: root

    property string title: "Acción destructiva"
    property string message: "Esta acción no se puede deshacer."
    property string confirmText: "Eliminar"
    property string cancelText: "Cancelar"
    property string keyword: "ELIMINAR"
    property string keywordPrompt: "Escribe \"" + root.keyword + "\" para confirmar:"
    property bool open: false

    signal confirmed()
    signal cancelled()

    objectName: "DestructiveActionDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: message + ". Escribe " + keyword + " para confirmar."

    visible: open

    DestructiveDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        keyword: root.keyword
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
