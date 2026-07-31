import QtQuick
import "../../components"

MichiErrorState {
    id: root

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Library Error State")
    objectName: "libraryErrorState"
    focus: true

    property string actionText: qsTr("Reintentar")

    signal actionRequested()

    title: qsTr("Error al cargar la biblioteca")
    message: qsTr("Ocurrió un problema al obtener los datos. Verifica tu conexión o la configuración de fuentes.")
    primaryActionText: root.actionText
    primaryActionObjectName: "errorStateActionButton"

    onPrimaryActionRequested: root.actionRequested()
}
