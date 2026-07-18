import QtQuick

MichiEmptyState {
    title: qsTr("No se pudo completar la operación")
    iconName: "error"
    primaryActionText: "Reintentar"
    Accessible.name: title
    Accessible.description: message + (details !== "" ? ". " + details : "")
}
