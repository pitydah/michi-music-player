import QtQuick

MichiEmptyState {
    title: qsTr("Cargando")
    message: qsTr("Espera mientras se prepara el contenido.")
    iconName: "library"
    busy: true
    Accessible.name: title
    Accessible.description: message
}
