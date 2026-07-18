import QtQuick

MichiEmptyState {
    title: qsTr("No disponible")
    message: qsTr("Esta función no está disponible en el estado actual.")
    iconName: "warning"
    Accessible.name: title
    Accessible.description: message
}
