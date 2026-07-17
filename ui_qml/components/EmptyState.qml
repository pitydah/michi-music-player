import QtQuick
import "../theme"
import "states"

MichiEmptyState {
    id: root

    property alias iconText: root.iconName
    property alias subtitle: root.message
    property alias actionText: root.primaryActionText
    property bool showAction: false

    signal actionClicked()

    onPrimaryActionRequested: root.actionClicked()
}
