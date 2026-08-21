import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiDialog {
    id: root
    objectName: "playlistCreateDialog"
    title: qsTr("New Playlist")
    property string errorText: ""
    signal playlistCreated(string name)

    standardButtons: Dialog.NoButton
    width: 420
    modal: true

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md
        MichiTextField {
            id: nameField
            objectName: "playlistNameField"
            Layout.fillWidth: true
            placeholderText: qsTr("Playlist name")
            accessibleName: qsTr("Playlist name")
            onAccepted: root._submit()
        }
        MichiText {
            visible: root.errorText !== ""
            text: root.errorText
            role: "technical"
            technical: true
            color: MichiPalette.error
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: MichiSpacing.sm
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                accessibleName: qsTr("Cancel create playlist")
                onClicked: root.close()
            }
            MichiButton {
                id: createButton
                text: qsTr("Create")
                variant: "primary"
                accessibleName: qsTr("Create playlist")
                enabled: nameField.text.trim().length > 0
                onClicked: root._submit()
            }
        }
    }

    function _submit() {
        var name = nameField.text.trim()
        if (name === "") {
            root.errorText = qsTr("Playlist name must not be empty")
            return
        }
        if (playlists.create_and_open_playlist(name)) {
            // M9-R1I: deterministic success flow — created/opened, then the
            // dialog closes (PLAYLISTS/<new id>, Recent rank 0, Detail shows).
            root.playlistCreated(name)
            root.close()
        } else {
            root.errorText = qsTr("A playlist with that name already exists")
            nameField.forceActiveFocus()
        }
    }

    onOpened: {
        nameField.text = ""
        root.errorText = ""
        nameField.forceActiveFocus()
    }

    onClosed: root.errorText = ""
}
