import QtQuick

MichiEmptyState {
    title: "Cargando"
    message: "Espera mientras se prepara el contenido."
    iconName: "refresh"
    busy: true
    Accessible.name: title
    Accessible.description: message
}
