import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root
    objectName: "headerViewSwitcher"

    property var modes: []
    property int currentIndex: 0
    property bool loading: false
    property string accessibleName: qsTr("Vistas disponibles")

    signal activated(int index)

    readonly property bool hasMultipleModes: root.modes && root.modes.length > 1

    visible: hasMultipleModes
    implicitWidth: hasMultipleModes ? modeRow.implicitWidth + 4 : 0
    implicitHeight: MichiTheme.minimumInteractiveSize

    Accessible.role: Accessible.ToolBar
    Accessible.name: root.accessibleName
    Accessible.description: qsTr("Cambia la presentación de la sección actual")

    Rectangle {
        anchors.centerIn: parent
        width: parent.width
        height: MichiTheme.minimumInteractiveSize
        radius: MichiTheme.radius.pill
        color: MichiTheme.colors.surfaceInput
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderInner
        }
    }

    Row {
        id: modeRow
        anchors.centerIn: parent
        spacing: 2

        Repeater {
            model: root.modes || []

            QQC2.Button {
                id: modeButton

                required property int index
                required property var modelData
                readonly property bool selected: index === root.currentIndex

                width: MichiTheme.minimumInteractiveSize
                height: MichiTheme.minimumInteractiveSize
                enabled: !root.loading
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                activeFocusOnTab: enabled && visible

                Accessible.role: Accessible.Button
                Accessible.name: modelData.label || modelData.tooltip || qsTr("Vista")
                Accessible.description: modelData.description || Accessible.name
                Accessible.checked: selected

                background: Rectangle {
                    radius: MichiTheme.radius.pill
                    color: modeButton.down
                           ? MichiTheme.colors.surfacePressed
                           : modeButton.selected
                             ? MichiTheme.colors.accentSelection
                             : modeButton.hovered
                               ? MichiTheme.colors.surfaceHover
                               : "transparent"
                    border.width: modeButton.activeFocus
                                  ? MichiTheme.focusWidth
                                  : modeButton.selected
                                    ? MichiTheme.borderWidth
                                    : 0
                    border.color: modeButton.activeFocus
                                  ? MichiTheme.colors.borderFocus
                                  : MichiTheme.colors.borderActive

                    Behavior on color {
                        enabled: !MichiTheme.reducedMotion
                        ColorAnimation { duration: MichiTheme.motionFast }
                    }
                }

                contentItem: MichiIcon {
                    anchors.centerIn: parent
                    source: modeButton.modelData.icon || ""
                    size: 19
                    color: modeButton.selected
                           ? MichiTheme.colors.accentBlue
                           : modeButton.hovered
                             ? MichiTheme.colors.textPrimary
                             : MichiTheme.colors.textSecondary
                    accessibleName: ""
                }

                onClicked: root.activated(index)

                QQC2.ToolTip {
                    visible: modeButton.hovered
                    delay: 450
                    text: modeButton.modelData.label ||
                          modeButton.modelData.tooltip ||
                          qsTr("Vista")
                }
            }
        }
    }
}
