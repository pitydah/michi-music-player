import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string placeholderText: qsTr("Buscar...")
    property string text: ""
    property bool loading: false
    property int debounceMs: 0
    property string accessibleName: "Buscar..."
    property string accessibleDescription: ""
    property bool _clearing: false

    signal searchTextChanged(string newText)
    signal searchSubmitted(string text)
    signal clearRequested()

    function forceInputFocus() {
        field.forceActiveFocus()
        field.selectAll()
    }

    function clear() {
        if (root.text === "")
            return
        debounceTimer.stop()
        root._clearing = true
        root.text = ""
        field.text = ""
        root._clearing = false
        field.forceActiveFocus()
        root.clearRequested()
    }

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

            MichiIcon {
                anchors.verticalCenter: parent.verticalCenter
                iconKey: "search"
                size: 18
                color: MichiTheme.colors.textMuted
                visible: !root.loading
                accessibleName: qsTr("Buscar")
            }

            QQC2.TextField {
                id: field
                height: parent.height
                width: parent.width - (clearBtn.visible ? clearBtn.width : 0) - 18 - parent.spacing - parent.anchors.leftMargin - parent.anchors.rightMargin
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                selectionColor: MichiTheme.colors.accentSelection
                placeholderText: root.placeholderText
                placeholderTextColor: MichiTheme.colors.textMuted
                text: root.text
                enabled: !root.loading
                activeFocusOnTab: enabled && visible
                verticalAlignment: TextInput.AlignVCenter
                background: Item { }

                onTextChanged: {
                    root.text = text
                    if (root._clearing)
                        return
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
                        root.clear()
                        event.accepted = true
                    }
                }

                Accessible.role: Accessible.EditableText
                Accessible.name: root.accessibleName
            }

            MichiIconButton {
                id: clearBtn
                controlObjectName: "searchClearButton"
                iconSource: "../../icons/clear.svg"
                tooltipText: "Limpiar"
                btnSize: Math.min(root.height - MichiTheme.spacing.xs * 2, 28)
                visible: root.text !== ""
                accessibleName: "Limpiar búsqueda"
                onClicked: root.clear()
            }
        }
    }
}
