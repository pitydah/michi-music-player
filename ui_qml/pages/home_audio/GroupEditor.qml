import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "homeAudio.groupEditor"

    property var availableZones: []
    property var selectedZoneIds: []

    signal groupCreated(string name, var zoneIds)
    signal groupCancelled()

    implicitHeight: 350

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de grupos"

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        variant: "elevated"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Editor de grupos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.role: Accessible.Heading
                Accessible.name: "Editor de grupos"
            }

            TextField {
                id: groupNameField
                width: parent.width
                placeholderText: "Nombre del grupo"
                objectName: "groupEditor.nameField"
                Accessible.name: "Nombre del grupo"
                KeyNavigation.tab: zoneList
            }

            Text {
                text: "Selecciona zonas para agrupar:"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            ListView {
                id: zoneList
                width: parent.width
                height: Math.min(contentHeight, 240)
                model: root.availableZones
                clip: true
                focus: true
                objectName: "groupEditor.zoneList"

                delegate: Rectangle {
                    width: parent.width
                    height: 48
                    color: root.selectedZoneIds.indexOf(modelData.id) >= 0 ? MichiTheme.colors.accentSurface : "transparent"
                    radius: MichiTheme.radiusSm
                    border.color: root.selectedZoneIds.indexOf(modelData.id) >= 0 ? MichiTheme.colors.accentBlue : "transparent"
                    border.width: 1
                    objectName: "groupEditor.zoneItem." + index

                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.name || "Zona"
                    Accessible.selected: root.selectedZoneIds.indexOf(modelData.id) >= 0

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            var idx = root.selectedZoneIds.indexOf(modelData.id)
                            if (idx >= 0) {
                                var arr = root.selectedZoneIds.slice()
                                arr.splice(idx, 1)
                                root.selectedZoneIds = arr
                            } else {
                                root.selectedZoneIds = root.selectedZoneIds.concat([modelData.id])
                            }
                        }
                    }

                    Keys.onSpacePressed: {
                        var idx = root.selectedZoneIds.indexOf(modelData.id)
                        if (idx >= 0) {
                            var arr = root.selectedZoneIds.slice()
                            arr.splice(idx, 1)
                            root.selectedZoneIds = arr
                        } else {
                            root.selectedZoneIds = root.selectedZoneIds.concat([modelData.id])
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md
                        text: modelData.name || "Zona"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Crear grupo"
                    variant: "primary"
                    enabled: root.selectedZoneIds.length > 1
                    onClicked: root.groupCreated(groupNameField.text || "Grupo", root.selectedZoneIds)
                    objectName: "groupEditor.createButton"
                    Accessible.name: "Crear grupo"
                    Accessible.description: "Requiere al menos 2 zonas"
                    KeyNavigation.tab: cancelBtn
                }

                MichiButton {
                    id: cancelBtn
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.groupCancelled()
                    objectName: "groupEditor.cancelButton"
                    Accessible.name: "Cancelar"
                    KeyNavigation.tab: groupNameField
                }
            }
        }
    }
}
