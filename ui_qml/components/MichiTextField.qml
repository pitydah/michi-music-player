import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property string label: ""
    property string placeholderText: ""
    property string helperText: ""
    property string errorText: ""
    property string text: ""
    property bool readOnly: false
    property bool loading: false
    property int maxLength: 0
    property string validationState: "none"
    property string accessibleName: root.label !== "" ? root.label : root.placeholderText
    property string accessibleDescription: root.errorText !== "" ? root.errorText : root.helperText

    signal accepted()
    signal textEdited(string newText)


    implicitHeight: fieldBackground.height + (root.label !== "" ? labelText.height + MichiTheme.spacing.xs : 0)
    implicitWidth: 260

    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    function _borderColor() {
        if (root.validationState === "error") return MichiTheme.colors.borderError
        if (field.activeFocus) return MichiTheme.colors.borderFocus
        if (field.hovered) return MichiTheme.colors.borderHover
        return MichiTheme.colors.borderCard
    }

    Text {
        id: labelText
        anchors.left: parent.left
        anchors.leftMargin: MichiTheme.spacing.xs
        anchors.bottom: fieldBackground.top
        anchors.bottomMargin: MichiTheme.spacing.xxs
        text: root.label
        color: MichiTheme.colors.textSecondary
        font.pixelSize: MichiTheme.typography.captionSize
        visible: root.label !== ""
    }

    Rectangle {
        id: fieldBackground
        anchors.left: parent.left
        anchors.right: parent.right
        height: MichiTheme.minimumInteractiveSize
        y: root.label !== "" ? labelText.height + MichiTheme.spacing.xs : 0
        radius: MichiTheme.radius.sm
        color: root.loading ? MichiTheme.colors.surfaceDisabled
             : root.readOnly ? MichiTheme.colors.surfaceSubtle
             : MichiTheme.colors.surfaceInput
        border.width: field.activeFocus || root.validationState === "error" ? MichiTheme.focusWidth : MichiTheme.borderWidth
        border.color: root._borderColor()

        QQC2.TextField {
            id: field
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.rightMargin: MichiTheme.spacing.md
            anchors.topMargin: MichiTheme.spacing.xs
            anchors.bottomMargin: MichiTheme.spacing.xs
            font.pixelSize: MichiTheme.typography.bodySize
            color: MichiTheme.colors.textPrimary
            selectionColor: MichiTheme.colors.accentSelection
            placeholderText: root.placeholderText
            placeholderTextColor: MichiTheme.colors.textMuted
            readOnly: root.readOnly || root.loading
            text: root.text
            activeFocusOnTab: enabled && visible
            verticalAlignment: TextInput.AlignVCenter
            maximumLength: root.maxLength > 0 ? root.maxLength : 32767

            onTextChanged: root.text = text
            onTextEdited: root.textEdited(text)
            onAccepted: root.accepted()

            Accessible.role: Accessible.EditableText
            Accessible.name: root.accessibleName
        }

        Text {
            id: charLimit
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.verticalCenter: parent.verticalCenter
            text: root.maxLength > 0 ? (root.text.length + "/" + root.maxLength) : ""
            color: root.text.length >= root.maxLength ? MichiTheme.colors.error : MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root.maxLength > 0
        }
    }

    Text {
        id: bottomText
        anchors.left: parent.left
        anchors.leftMargin: MichiTheme.spacing.xs
        anchors.top: fieldBackground.bottom
        anchors.topMargin: MichiTheme.spacing.xxs
        text: root.errorText !== "" ? root.errorText : root.helperText
        color: root.errorText !== "" ? MichiTheme.colors.error : MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.metaSize
        visible: root.errorText !== "" || root.helperText !== ""
    }
}
