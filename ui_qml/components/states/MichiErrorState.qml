import QtQuick

MichiEmptyState {
    title: "No se pudo completar la operación"
    iconName: "error"
    primaryActionText: "Reintentar"
    Accessible.name: title
    Accessible.description: message + (details !== "" ? ". " + details : "")
}
