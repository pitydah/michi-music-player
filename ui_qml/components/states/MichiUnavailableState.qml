import QtQuick
import "../../theme"

MichiEmptyState {
    title: qsTr("No disponible")
    message: qsTr("Esta función no está disponible en el estado actual.")
    iconSource: "../../../icons/states/unavailable.svg"
    iconColor: MichiTheme.colors.textSecondary
    Accessible.name: title
    Accessible.description: message
}
