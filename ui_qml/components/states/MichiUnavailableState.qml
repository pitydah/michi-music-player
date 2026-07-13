import QtQuick

MichiEmptyState {
    title: "No disponible"
    message: "Esta función no está disponible en el estado actual."
    iconName: "warning"
    Accessible.name: title
    Accessible.description: message
}
