import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    objectName: "ecosystemSpacesPage"
    signal navigationRequested(string routeId)
    eyebrow: qsTr("MICHI HOME")
    title: qsTr("Spaces")
    subtitle: qsTr("Organiza dispositivos de tu Home. Un espacio no es un grupo de reproducción.")
    iconName: "pin"
    statusText: ecosystemOperations.spacesAvailable ? qsTr("Local") : qsTr("Home no disponible")
    statusTone: ecosystemOperations.spacesAvailable ? "neutral" : "warning"
    onBackRequested: root.navigationRequested("ecosystem")

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.md
        MichiTextField {
            id: newSpaceName
            Layout.fillWidth: true
            placeholderText: qsTr("Nombre del espacio")
            accessibleName: qsTr("Nombre del nuevo espacio")
            maximumLength: 48
            enabled: ecosystemOperations.spacesAvailable && ecosystemOperations.ownerAuthorized && !ecosystemOperations.busy
            onAccepted: {
                if (createSpace.enabled) {
                    ecosystemOperations.createSpace(newSpaceName.text)
                    newSpaceName.text = ""
                }
            }
        }
        MichiButton {
            id: createSpace
            text: qsTr("Crear")
            enabled: newSpaceName.text.trim().length > 0 && !ecosystemOperations.busy
                && ecosystemOperations.spacesAvailable && ecosystemOperations.ownerAuthorized
            onClicked: {
                ecosystemOperations.createSpace(newSpaceName.text)
                newSpaceName.text = ""
            }
        }
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.lastErrorText.length > 0
        text: ecosystemOperations.lastErrorText
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.auditWarningText.length > 0
        text: ecosystemOperations.auditWarningText
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.spaces.length === 0
        text: qsTr("Todavía no hay espacios. Crea Living, Dormitorio o Escritorio.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: ecosystemOperations.spaces
        delegate: MichiGlassSurface {
            id: spaceCard
            required property var modelData
            property bool confirmDelete: false
            Layout.fillWidth: true
            implicitHeight: content.implicitHeight + 2 * contentPadding
            elevation: "subtle"
            ColumnLayout {
                id: content
                anchors.fill: parent
                spacing: MichiSpacing.md
                RowLayout {
                    Layout.fillWidth: true
                    MichiText { text: modelData.name; role: "section"; Layout.fillWidth: true }
                    MichiText { text: qsTr("%1 dispositivo(s)").arg(modelData.deviceCount); role: "secondary" }
                }
                Repeater {
                    model: modelData.members
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        MichiText { text: modelData.name; role: "secondary"; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        MichiButton {
                            text: qsTr("Quitar")
                            variant: "ghost"
                            enabled: !ecosystemOperations.busy && ecosystemOperations.ownerAuthorized
                            onClicked: ecosystemOperations.unassignDevice(spaceCard.modelData.id, modelData.id)
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    MichiTextField {
                        id: renameField
                        Layout.fillWidth: true
                        text: modelData.name
                        accessibleName: qsTr("Renombrar espacio")
                        maximumLength: 48
                        enabled: !ecosystemOperations.busy && ecosystemOperations.ownerAuthorized
                    }
                    MichiButton {
                        text: qsTr("Guardar")
                        variant: "ghost"
                        enabled: !ecosystemOperations.busy && ecosystemOperations.ownerAuthorized
                        onClicked: ecosystemOperations.renameSpace(modelData.id, renameField.text)
                    }
                    MichiButton {
                        text: spaceCard.confirmDelete ? qsTr("Confirmar eliminación") : qsTr("Eliminar")
                        variant: "danger"
                        enabled: !ecosystemOperations.busy && ecosystemOperations.ownerAuthorized && modelData.deviceCount === 0
                        onClicked: {
                            if (spaceCard.confirmDelete)
                                ecosystemOperations.deleteSpace(spaceCard.modelData.id)
                            else
                                spaceCard.confirmDelete = true
                        }
                    }
                }
            }
        }
    }
    MichiText {
        Layout.fillWidth: true
        text: qsTr("Para asignar un dispositivo, abre Tus dispositivos y selecciona su Space.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
}
