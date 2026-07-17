import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Field"
    objectName: "searchField"
    focus: true
    id: root

    property string placeholderText: "Buscar..."
    property alias text: searchInput.text
    property bool fieldFocused: false
    property string accessibleName: placeholderText
    property string accessibleDescription: ""

    signal searchTextChanged(string newText)
    signal searchSubmitted(string text)
    signal searchRequested(string text)
    signal textChangedByUser(string text)
    signal clearRequested()

    implicitHeight: 38
    implicitWidth: 280

    InputMaterial {
        anchors.fill: parent
        focused: root.fieldFocused
        hoveredInput: hover.hovered
        radius: MichiTheme.radius.sm
    }

    TextInput {
        Accessible.role: Accessible.EditableText

        Accessible.name: "Campo de texto"

        id: searchInput
        activeFocusOnTab: true

        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.topMargin: MichiTheme.spacing.xs
        anchors.bottomMargin: MichiTheme.spacing.xs
        color: MichiTheme.colors.textPrimary
        font.pixelSize: MichiTheme.typography.bodySize
        selectionColor: MichiTheme.colors.accentSelection
        clip: true
        verticalAlignment: TextInput.AlignVCenter

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.placeholderText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            visible: parent.text === "" && !parent.activeFocus
        }

        Accessible.description: root.accessibleDescription

        onTextChanged: root.searchTextChanged(text)
        onTextEdited: root.textChangedByUser(text)
        onAccepted: {
            root.searchSubmitted(text)
            root.searchRequested(text)
        }
        onActiveFocusChanged: root.fieldFocused = activeFocus
        Keys.onEscapePressed: function(event) {
            if (text !== "") {
                text = ""
                root.clearRequested()
                event.accepted = true
            }
        }

        HoverHandler { id: hover; cursorShape: Qt.IBeamCursor }
    }
}
