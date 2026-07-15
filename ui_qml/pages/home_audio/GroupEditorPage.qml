import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
import QtQuick.Layouts
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
=======
import QtQuick.Controls as QQC2
import QtQuick.Layouts
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    focus: true
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var availableZones: []
    property var selectedZoneIds: []
    property string groupName: ""
    property bool editMode: false
    property string originalGroupName: ""

    signal groupCreated(string name, var zoneIds)
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
    focus: true

    property var availableZones: []
    property var selectedZoneIds: []
    property string groupName: ""
    property bool editMode: false
    property string originalGroupName: ""

    signal groupCreated(string name, var zoneIds)
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    signal groupUpdated(string name, var zoneIds)
    signal groupCancelled()

    objectName: "groupEditorPage"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de grupos"

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    AsyncStateView {
        id: asyncView
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    FocusScope {
        id: focusScope
>>>>>>> Stashed changes
        anchors.fill: parent
        state: root.availableZones.length === 0 ? AsyncStateView.EMPTY : AsyncStateView.READY
        title: "Sin zonas disponibles"
        message: "No hay zonas disponibles para agrupar. Conecta dispositivos primero."
        iconName: "group"

<<<<<<< Updated upstream
        readyContent: Flickable {
=======
        Keys.onEscapePressed: root.backClicked()

        Flickable {
=======
    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root.availableZones.length === 0 ? AsyncStateView.EMPTY : AsyncStateView.READY
        title: "Sin zonas disponibles"
        message: "No hay zonas disponibles para agrupar. Conecta dispositivos primero."
        iconName: "group"

        readyContent: Flickable {
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            activeFocusOnTab: true
            objectName: "groupEditorFlickable"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            focus: true
=======
            activeFocusOnTab: true
            objectName: "groupEditorFlickable"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                MichiButton {
                    id: backBtn
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.groupCancelled()
                    objectName: "groupEditorBackButton"
                    Accessible.name: "Volver"
                    Keys.onReturnPressed: root.groupCancelled()
                    Keys.onSpacePressed: root.groupCancelled()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
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
>>>>>>> Stashed changes
                }

                Text {
                    text: root.editMode ? "Editar grupo" : "Crear grupo"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: root.editMode ? "Editar grupo" : "Crear grupo"
                    objectName: "groupEditorTitle"
                }

                QQC2.TextField {
                    id: groupNameField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Nombre del grupo"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.groupName
                    onTextChanged: root.groupName = text
                    objectName: "groupEditorNameField"
                    Accessible.name: "Nombre del grupo"
                    Accessible.description: "Nombre para identificar el grupo de zonas"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: zoneList
                    KeyNavigation.backtab: backBtn
                }

                Text {
                    text: root.editMode ? "Zonas en el grupo (selecciona para cambiar):" : "Selecciona zonas para agrupar:"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Repeater {
                    id: zoneList
                    model: root.availableZones

                    Rectangle {
                        width: parent.width
                        height: 48
                        color: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? MichiTheme.colors.accentSurface
                            : "transparent"
                        radius: MichiTheme.radiusSm
                        border.color: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? MichiTheme.colors.accentBlue
                            : "transparent"
                        border.width: 1
                        objectName: "groupEditorZoneItem_" + index
                        Accessible.name: modelData.name || "Zona"
                        Accessible.description: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? "Seleccionada" : "No seleccionada"

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

                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: MichiTheme.spacing.md
                            anchors.right: parent.right
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            Text {
                                text: modelData.name || "Zona"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                width: parent.width - 80
                                elide: Text.ElideRight
                            }

<<<<<<< Updated upstream
=======
                            MichiButton {
                                id: cancelBtnGroup
                                text: "Cancelar"
                                variant: "ghost"
                                onClicked: root.backClicked()
                                objectName: "groupEditor.cancelButton"
                                Accessible.name: "Cancelar"
                                KeyNavigation.tab: groupNameField
=======
                MichiButton {
                    id: backBtn
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.groupCancelled()
                    objectName: "groupEditorBackButton"
                    Accessible.name: "Volver"
                    Keys.onReturnPressed: root.groupCancelled()
                    Keys.onSpacePressed: root.groupCancelled()
                }

                Text {
                    text: root.editMode ? "Editar grupo" : "Crear grupo"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: root.editMode ? "Editar grupo" : "Crear grupo"
                    objectName: "groupEditorTitle"
                }

                QQC2.TextField {
                    id: groupNameField
                    width: parent.width
                    height: MichiTheme.rowHeightComfortable
                    placeholderText: "Nombre del grupo"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    text: root.groupName
                    onTextChanged: root.groupName = text
                    objectName: "groupEditorNameField"
                    Accessible.name: "Nombre del grupo"
                    Accessible.description: "Nombre para identificar el grupo de zonas"

                    background: Rectangle {
                        radius: MichiTheme.radiusSm
                        color: MichiTheme.colors.surfaceInput
                        border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                        border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                    }
                    KeyNavigation.tab: zoneList
                    KeyNavigation.backtab: backBtn
                }

                Text {
                    text: root.editMode ? "Zonas en el grupo (selecciona para cambiar):" : "Selecciona zonas para agrupar:"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Repeater {
                    id: zoneList
                    model: root.availableZones

                    Rectangle {
                        width: parent.width
                        height: 48
                        color: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? MichiTheme.colors.accentSurface
                            : "transparent"
                        radius: MichiTheme.radiusSm
                        border.color: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? MichiTheme.colors.accentBlue
                            : "transparent"
                        border.width: 1
                        objectName: "groupEditorZoneItem_" + index
                        Accessible.name: modelData.name || "Zona"
                        Accessible.description: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            ? "Seleccionada" : "No seleccionada"

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

                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: MichiTheme.spacing.md
                            anchors.right: parent.right
                            anchors.rightMargin: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            Text {
                                text: modelData.name || "Zona"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                width: parent.width - 80
                                elide: Text.ElideRight
                            }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            StatusBadge {
                                text: root.selectedZoneIds.indexOf(modelData.id) >= 0 ? "Seleccionada" : ""
                                kind: "success"
                                visible: root.selectedZoneIds.indexOf(modelData.id) >= 0
                            }
                        }

                        Keys.onReturnPressed: {
                            var idx = root.selectedZoneIds.indexOf(modelData.id)
                            if (idx >= 0) {
                                var arr = root.selectedZoneIds.slice()
                                arr.splice(idx, 1)
                                root.selectedZoneIds = arr
                            } else {
                                root.selectedZoneIds = root.selectedZoneIds.concat([modelData.id])
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                            }
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                StatusBadge {
                    text: "Requiere Snapcast para agrupar zonas"
                    kind: "info"
                    visible: root.ha && !root.ha.groupingSupported
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                Text {
                    text: root.selectedZoneIds.length + " zona(s) seleccionada(s)"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                Text {
                    text: root.selectedZoneIds.length < 2 ? "Selecciona al menos 2 zonas para crear un grupo" : ""
                    color: MichiTheme.colors.warning
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: root.selectedZoneIds.length < 2
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    objectName: "groupEditorActions"

                    MichiButton {
                        id: createBtn
                        text: root.editMode ? "Guardar cambios" : "Crear grupo"
                        variant: "primary"
                        enabled: root.groupName.trim() !== "" && root.selectedZoneIds.length >= 2
                        onClicked: {
                            if (root.editMode) {
                                root.groupUpdated(root.groupName, root.selectedZoneIds)
                            } else {
                                root.groupCreated(root.groupName, root.selectedZoneIds)
                            }
                        }
                        objectName: "groupEditorCreateButton"
                        Accessible.name: root.editMode ? "Guardar cambios del grupo" : "Crear grupo con zonas seleccionadas"
                        Accessible.description: root.groupName.trim() === "" ? "Escribe un nombre para el grupo" : ""
                        KeyNavigation.tab: cancelBtn
                        KeyNavigation.backtab: zoneList
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: cancelBtn
                        text: "Cancelar"
                        variant: "ghost"
                        onClicked: root.groupCancelled()
                        objectName: "groupEditorCancelButton"
                        Accessible.name: "Cancelar edición de grupo"
                        KeyNavigation.backtab: createBtn
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                }
            }
        }
    }
}
