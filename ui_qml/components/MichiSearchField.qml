import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string placeholderText: qsTr("Buscar…")
    property string text: ""
    property bool loading: false
    property int debounceMs: 0
    property string accessibleName: qsTr("Buscar")
    property string accessibleDescription: qsTr("Escribe para filtrar el contenido visible")
    property bool _clearing: false

    signal searchTextChanged(string newText)
    signal searchSubmitted(string text)
    signal clearRequested()

    function forceInputFocus() {
        field.forceActiveFocus()
        field.selectAll()
    }

    function setTextSilently(value) {
        var normalized = value || ""
        if (root.text === normalized && field.text === normalized)
            return
        debounceTimer.stop()
        root._clearing = true
        root.text = normalized
        field.text = normalized
        root._clearing = false
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

    function forceEditorFocus() {
        field.forceActiveFocus()
        field.selectAll()
    }

    function clearSearch(refocus) {
        debounceTimer.stop()
        var hadText = root.text !== ""
        root.text = ""
        if (hadText) {
            root.clearRequested()
            root.searchTextChanged("")
        }
        if (refocus)
            field.forceActiveFocus()
    }

    Timer {
        id: debounceTimer
        interval: Math.max(0, root.debounceMs)
        repeat: false
        onTriggered: root.searchTextChanged(root.text)
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.pill
        color: MichiTheme.colors.surfaceInput
        border.width: field.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
        border.color: field.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

        Behavior on border.color {
            ColorAnimation { duration: MichiTheme.motionFast }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.xs
            anchors.topMargin: MichiTheme.spacing.xs
            anchors.bottomMargin: MichiTheme.spacing.xs
            spacing: MichiTheme.spacing.sm

            MichiIcon {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                iconKey: "search"
                size: 18
                color: MichiTheme.colors.textMuted
                visible: !root.loading
                accessibleName: qsTr("Buscar")
            }

            QQC2.BusyIndicator {
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
                visible: root.loading
                running: visible
                Accessible.role: Accessible.Indicator
                Accessible.name: qsTr("Actualizando resultados")
            }

            QQC2.TextField {
                id: field
                Layout.fillWidth: true
                Layout.fillHeight: true
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                selectionColor: MichiTheme.colors.accentSelection
                placeholderText: root.placeholderText
                placeholderTextColor: MichiTheme.colors.textMuted
                text: root.text
                activeFocusOnTab: visible
                verticalAlignment: TextInput.AlignVCenter
                selectByMouse: true
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

                onAccepted: {
                    debounceTimer.stop()
                    root.searchTextChanged(root.text)
                    root.searchSubmitted(root.text)
                }

                Keys.onEscapePressed: function(event) {
                    if (root.text !== "") {
                        root.clearSearch(true)
                        event.accepted = true
                    }
                }

                Accessible.role: Accessible.EditableText
                Accessible.name: root.accessibleName
                Accessible.description: root.accessibleDescription
            }

            MichiIconButton {
                id: clearBtn
                controlObjectName: "searchClearButton"
                iconSource: "../../icons/nav_back.svg"
                tooltipText: qsTr("Limpiar búsqueda")
                btnSize: Math.min(root.height - MichiTheme.spacing.xs * 2, 28)
                visible: root.text !== ""
                accessibleName: qsTr("Limpiar búsqueda")
                transform: Rotation { angle: 45 }
                onClicked: root.clearSearch(true)
            }
        }
    }
}
