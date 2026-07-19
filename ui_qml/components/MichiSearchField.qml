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

            Image {
                anchors.verticalCenter: parent.verticalCenter
                width: 18
                height: 18
                source: "../../icons/sidebar/search.svg"
                sourceSize.width: 18
                sourceSize.height: 18
                fillMode: Image.PreserveAspectFit
                visible: !root.loading
                Accessible.role: Accessible.Graphic
                Accessible.name: "Buscar"
                Accessible.description: "Icono de búsqueda"
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

                Accessible.role: Accessible.EditableText
                Accessible.name: root.accessibleName
            }

            MichiIconButton {
                id: clearBtn
                iconSource: "../../icons/nav_back.svg"
                tooltipText: "Limpiar"
                btnSize: Math.min(root.height - MichiTheme.spacing.xs * 2, 28)
                visible: root.text !== ""
                accessibleName: "Limpiar búsqueda"
                transform: Rotation { angle: 45 }
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
