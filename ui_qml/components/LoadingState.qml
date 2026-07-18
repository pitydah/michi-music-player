import QtQuick
import "../theme"
import "states"

MichiEmptyState {
    id: root

    property alias subtitle: root.message
    property bool showProgress: true

    title: qsTr("Cargando...")
    busy: root.showProgress
    iconName: ""
}
