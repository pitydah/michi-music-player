import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "groupEditorPage"
    focus: true

    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property var availableReceivers: typeof homeAudioBridge !== "undefined"
                                     ? homeAudioBridge.receiverList : []
    property var selectedReceiverIds: []
    property string groupId: ""
    property string groupName: ""
    property bool editMode: groupId !== ""
    property string feedback: ""
    property bool feedbackError: false
    readonly property bool operationBusy: root.bridge
                                               ? root.bridge.operationInProgress : false

    Accessible.role: Accessible.Pane
    Accessible.name: root.editMode ? qsTr("Editar grupo") : qsTr("Crear grupo")

    signal groupCancelled()

    function groupForId(id) {
        var groups = root.bridge && root.bridge.groups ? root.bridge.groups : []
        for (var index = 0; index < groups.length; ++index) {
            if (String(groups[index].id || "") === String(id || ""))
                return groups[index]
        }
        return null
    }

    function routeEnter(route, params) {
        root.groupId = params ? String(params.groupId || params.group_id || "") : ""
        root.feedback = ""
        root.feedbackError = false
        if (root.bridge)
            root.bridge.refresh()
        var group = root.groupForId(root.groupId)
        root.groupName = group ? String(group.name || "") : ""
        root.selectedReceiverIds = group
                                   ? (group.members || group.devices || []).slice(0)
                                   : []
    }

    function toggleReceiver(receiverId) {
        var next = root.selectedReceiverIds.slice(0)
        var index = next.indexOf(receiverId)
        if (index >= 0)
            next.splice(index, 1)
        else
            next.push(receiverId)
        root.selectedReceiverIds = next
    }

    function showResult(result) {
        root.feedbackError = !result || result.ok === false
        if (root.feedbackError) {
            root.feedback = qsTr("No se pudo guardar el grupo: %1")
                                .arg(result && result.error
                                     ? result.error
                                     : (result && result.errors && result.errors.length > 0
                                        ? result.errors.join(", ")
                                        : qsTr("error desconocido")))
            return
        }
        if (result.pending) {
            root.feedback = qsTr("Guardando grupo…")
            return
        }
        root.feedback = qsTr("Grupo guardado correctamente.")
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.back()
    }

    function submit() {
        if (!root.bridge || root.operationBusy)
            return
        var result = root.editMode
                     ? root.bridge.updateGroup(root.groupId, root.groupName, root.selectedReceiverIds)
                     : root.bridge.createGroup(root.groupName, root.selectedReceiverIds)
        root.showResult(result)
    }

    onGroupCancelled: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.back()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.lg

        RowLayout {
            Layout.fillWidth: true

            MichiButton {
                text: qsTr("Volver")
                variant: "ghost"
                onClicked: root.groupCancelled()
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: root.editMode ? qsTr("Editar grupo") : qsTr("Crear grupo")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }
        }

        QQC2.TextField {
            id: groupNameField
            Layout.fillWidth: true
            placeholderText: qsTr("Nombre del grupo")
            text: root.groupName
            onTextChanged: root.groupName = text
            Accessible.name: qsTr("Nombre del grupo")
        }

        SectionHeader {
            Layout.fillWidth: true
            text: qsTr("Receptores")
        }

        QQC2.Label {
            Layout.fillWidth: true
            visible: root.availableReceivers.length === 0
            text: qsTr("No hay receptores disponibles. Detecta o añade un receptor primero.")
            color: MichiTheme.colors.textMuted
            wrapMode: Text.WordWrap
        }

        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Repeater {
                    model: root.availableReceivers

                    QQC2.CheckBox {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.name || modelData.id || qsTr("Receptor")
                        checked: root.selectedReceiverIds.indexOf(String(modelData.id || "")) >= 0
                        enabled: modelData.available !== false
                        onClicked: root.toggleReceiver(String(modelData.id || ""))
                        Accessible.name: qsTr("Seleccionar receptor %1").arg(text)
                    }
                }
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            visible: root.feedback !== ""
            text: root.feedback
            color: root.feedbackError ? MichiTheme.colors.error : MichiTheme.colors.success
            wrapMode: Text.WordWrap
            Accessible.role: root.feedbackError ? Accessible.AlertMessage : Accessible.StaticText
        }

        QQC2.Label {
            Layout.fillWidth: true
            visible: root.selectedReceiverIds.length < 2
            text: qsTr("Selecciona al menos dos receptores.")
            color: MichiTheme.colors.warning
        }

        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("Cancelar")
                variant: "ghost"
                enabled: !root.operationBusy
                onClicked: root.groupCancelled()
            }

            MichiButton {
                text: root.editMode ? qsTr("Guardar cambios") : qsTr("Crear grupo")
                variant: "primary"
                enabled: !root.operationBusy
                         && root.groupName.trim() !== ""
                         && root.selectedReceiverIds.length >= 2
                onClicked: root.submit()
            }
        }
    }

    Connections {
        target: root.bridge
        function onOperationFinished(result) {
            if (root.operationBusy || root.feedback === qsTr("Guardando grupo…"))
                root.showResult(result)
        }
    }
}
