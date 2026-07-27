import QtQuick
import "states" as States
import "../theme"

States.MichiEmptyState {
    id: root

    property string iconText: ""

    title: qsTr("No disponible")
    message: qsTr("Esta función no está disponible en este momento.")
    iconSource: "../../icons/states/unavailable.svg"
    iconColor: MichiTheme.colors.textSecondary
}
