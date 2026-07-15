import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "groupEditorPage"

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property var availableZones: root.ha ? root.ha.zones : []
    property var selectedZoneIds: []

    signal backClicked()
    signal groupCreated(string name, var zoneIds)

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de grupos"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "groupEditor.focusScope"

        Keys.onEscapePressed: root.backClicked()

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        text: "< Volver"
                        variant: "ghost"
                        onClicked: root.backClicked()
                        objectName: "groupEditor.backButton"
                        Accessible.name: "Volver"
                        KeyNavigation.tab: groupNameField
                    }

                    Text {
                        text: "Editor de grupos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                        Accessible.role: Accessible.Heading
                    }
                }

                GlassMaterial {
                    width: parent.width
                    implicitHeight: column2.height + MichiTheme.spacing.xl * 2
                    radius: MichiTheme.radiusMd
                    variant: "elevated"

                    Column {
                        id: column2
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Selecciona zonas para agrupar:"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        TextField {
                            id: groupNameField
                            width: parent.width
                            placeholderText: "Nombre del grupo (opcional)"
                            objectName: "groupEditor.nameField"
                            Accessible.name: "Nombre del grupo"
                            KeyNavigation.tab: zoneList
                        }

                        ListView {
                            id: zoneList
                            width: parent.width
                            height: Math.min(contentHeight, 300)
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

                            Text {
                                anchors.centerIn: parent
                                visible: parent.count === 0
                                text: "No hay zonas disponibles."
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                            }
                        }

                        Text {
                            text: root.selectedZoneIds.length > 0
                                ? root.selectedZoneIds.length + " zona(s) seleccionada(s)"
                                : "Selecciona al menos 2 zonas para crear un grupo"
                            color: root.selectedZoneIds.length > 1 ? MichiTheme.colors.success : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
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
                                Accessible.description: "Requiere al menos 2 zonas seleccionadas"
                                KeyNavigation.tab: cancelBtnGroup
                            }

                            MichiButton {
                                id: cancelBtnGroup
                                text: "Cancelar"
                                variant: "ghost"
                                onClicked: root.backClicked()
                                objectName: "groupEditor.cancelButton"
                                Accessible.name: "Cancelar"
                                KeyNavigation.tab: groupNameField
                            }
                        }
                    }
                }

                StatusBadge {
                    text: "Requiere Snapcast para agrupar zonas"
                    kind: "info"
                    visible: root.ha && !root.ha.groupingSupported
                }
            }
        }
    }
}
