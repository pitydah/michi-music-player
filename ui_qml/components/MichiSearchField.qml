import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    objectName: "michiSearchField"

    property string placeholderText: "Buscar..."
    property string text: ""
    property bool loading: false
    property int debounceMs: 0
    property string accessibleName: root.placeholderText
    property string accessibleDescription: ""

    signal searchTextChanged(string newText)
    signal searchSubmitted(string text)
    signal clearRequested()

    implicitHeight: MichiTheme.minimumInteractiveSize
    implicitWidth: 220

    Accessible.role: Accessible.EditableText
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.pill
        color: root.loading ? MichiTheme.colors.surfaceDisabled : MichiTheme.colors.surfaceInput
        border.width: field.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
        border.color: field.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.xs
            anchors.topMargin: MichiTheme.spacing.xs
            anchors.bottomMargin: MichiTheme.spacing.xs
            spacing: MichiTheme.spacing.sm

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "\uD83D\uDD0D"
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textMuted
                visible: !root.loading
            }

            QQC2.TextField {
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                id: field
                height: parent.height
                width: parent.width - clearBtn.width - MichiTheme.spacing.sm - parent.spacing - parent.anchors.leftMargin - parent.anchors.rightMargin
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                selectionColor: MichiTheme.colors.accentSelection
                placeholderText: root.placeholderText
                placeholderTextColor: MichiTheme.colors.textMuted
                text: root.text
                enabled: !root.loading
                activeFocusOnTab: enabled
                verticalAlignment: TextInput.AlignVCenter

                onTextChanged: {
                    root.text = text
                    if (root.debounceMs > 0) {
                        debounceTimer.restart()
                    } else {
                        root.searchTextChanged(text)
                    }
                }
                onAccepted: root.searchSubmitted(root.text)

                Timer {
                    id: debounceTimer
                    interval: root.debounceMs
                    onTriggered: root.searchTextChanged(root.text)
                }

                Keys.onEscapePressed: function(event) {
                    if (root.text !== "") {
                        root.text = ""
                        field.text = ""
                        root.clearRequested()
                        root.searchTextChanged("")
                        event.accepted = true
                    }
                }
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiIconButton {
                id: clearBtn
                iconText: "\u2715"
                tooltipText: "Limpiar"
                btnSize: Math.min(root.height - MichiTheme.spacing.xs * 2, 28)
                visible: root.text !== ""
                onClicked: {
                    root.text = ""
                    field.text = ""
                    field.forceActiveFocus()
                    root.clearRequested()
                    root.searchTextChanged("")
                }
            }
        }
    }
}
