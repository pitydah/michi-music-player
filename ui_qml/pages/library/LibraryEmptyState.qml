import QtQuick
import "../../components"

MichiEmptyState {
    id: root

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Library Empty State")
    objectName: "libraryEmptyState"
    focus: true

    property string actionText: qsTr("Refrescar")

    signal actionRequested()

    title: qsTr("Biblioteca vacía")
    message: qsTr("Agrega carpetas con música o refresca la biblioteca.")
    iconName: "library"
    primaryActionText: root.actionText
    primaryActionObjectName: "emptyStateActionButton"
    secondaryActionText: qsTr("Ajustes")

    onPrimaryActionRequested: root.actionRequested()
    onSecondaryActionRequested: {
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate("settings")
    }
}
