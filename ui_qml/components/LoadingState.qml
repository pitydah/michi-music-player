import QtQuick
import "../theme"
import "states"

MichiEmptyState {
    id: root

    property alias subtitle: root.message
    property bool showProgress: true

    title: "Cargando..."
    busy: root.showProgress
    iconName: ""
}
