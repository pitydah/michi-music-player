import QtQuick
import "../../theme"

MichiEmptyState {
    title: qsTr("No se pudo completar la operación")
    iconSource: "../../../icons/states/error.svg"
    iconColor: MichiTheme.colors.error
    primaryActionText: qsTr("Reintentar")
    Accessible.name: title
    Accessible.description: message + (details !== "" ? ". " + details : "")
}
