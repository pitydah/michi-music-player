import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    id: root

    property string placeholderText: "Buscar..."
    property string text: ""
    property bool fieldFocused: false

    signal searchTextChanged(string newText)
    signal searchSubmitted(string text)

    implicitHeight: 38
    implicitWidth: 280

    InputMaterial {
        anchors.fill: parent
        focused: root.fieldFocused
        hoveredInput: searchInput.hovered
        radius: MichiTheme.radiusSm
    }

    TextInput {
        id: searchInput
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

        property bool hovered: false

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.placeholderText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            visible: parent.text === "" && !parent.activeFocus
        }

        onTextChanged: root.searchTextChanged(text)
        onAccepted: root.searchSubmitted(text)
        onActiveFocusChanged: root.fieldFocused = activeFocus

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.IBeamCursor
            onEntered: searchInput.hovered = true
            onExited: searchInput.hovered = false
            onClicked: searchInput.forceActiveFocus()
        }
    }
}
