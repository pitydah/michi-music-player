import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Group Editor"
    objectName: "groupEditor"
    focus: true
    id: root

    property var availableZones: []
    property var selectedZoneIds: []

    signal groupCreated(string name, var zoneIds)
    signal groupCancelled()

    implicitHeight: 350

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
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: groupNameField
                width: parent.width
                placeholderText: "Nombre del grupo"
            }

            Text {
                text: "Selecciona zonas para agrupar:"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Repeater {
                model: root.availableZones

                Rectangle {
                    width: parent.width
                    height: 48
                    color: root.selectedZoneIds.indexOf(modelData.id) >= 0 ? MichiTheme.colors.accentSurface : "transparent"
                    radius: MichiTheme.radiusSm
                    border.color: root.selectedZoneIds.indexOf(modelData.id) >= 0 ? MichiTheme.colors.accentBlue : "transparent"
                    border.width: 1

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
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: root.groupCancelled()
                }
            }
        }
    }
}
