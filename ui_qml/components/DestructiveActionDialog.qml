import QtQuick
import "../theme"
import "dialogs"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Destructive Action"
    objectName: "destructiveActionDialog"
    focus: true
    id: root

    property string title: qsTr("Acción destructiva")
    property string message: qsTr("Esta acción no se puede deshacer.")
    property string confirmText: "Eliminar"
    property string cancelText: "Cancelar"
    property string keyword: "ELIMINAR"
    property string keywordPrompt: "Escribe \"" + root.keyword + "\" para confirmar:"
    property bool open: false

    signal confirmed()
    signal cancelled()


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
