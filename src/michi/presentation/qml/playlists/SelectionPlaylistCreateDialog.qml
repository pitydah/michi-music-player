import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiDialog {
    id: root

    property var selectionPayload: ({})
    property string errorText: ""
    signal createRequested(string name, var payload)

    title: qsTr("New playlist")
    width: 420
    standardButtons: Dialog.NoButton

    function begin(payload) {
        selectionPayload = payload
        errorText = ""
        nameField.text = ""
        open()
        nameField.forceActiveFocus()
    }

    function complete(success) {
        if (success)
            close()
        else
            errorText = qsTr("Choose a unique, non-empty playlist name.")
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        MichiTextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: qsTr("Playlist name")
            onAccepted: root.createRequested(text, root.selectionPayload)
        }
        MichiText {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            text: root.errorText
            role: "secondary"
            color: MichiPalette.error
            wrapMode: Text.Wrap
        }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                onClicked: root.close()
            }
            MichiButton {
                text: qsTr("Create and add")
                variant: "primary"
                enabled: nameField.text.trim().length > 0
                onClicked: root.createRequested(
                    nameField.text, root.selectionPayload)
            }
        }
    }
}
