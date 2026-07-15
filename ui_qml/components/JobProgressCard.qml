import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    id: root

    property string title: ""
    property string description: ""
    property real progress: 0.0
    property bool indeterminate: false
    property string statusText: ""
    property string statusVariant: "info"
    property bool cancelEnabled: false
    property string objectName: "jobProgressCard"

    signal cancelRequested()

    implicitWidth: 320
    implicitHeight: layout.implicitHeight + MichiTheme.spacing.lg * 2

    radius: MichiTheme.radiusMd
    color: MichiTheme.colors.surfaceCard
    border.width: MichiTheme.borderWidth
    border.color: {
        switch (root.statusVariant) {
            case "error": return MichiTheme.colors.error
            case "success": return MichiTheme.colors.success
            case "warning": return MichiTheme.colors.warning
            default: return MichiTheme.colors.borderCard
        }
    }

    Accessible.role: Accessible.Panel
    Accessible.name: root.title

    Column {
        id: layout
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.sm

        Text {
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            width: parent.width
            elide: Text.ElideRight
        }

        Text {
            text: root.description
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            width: parent.width
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        MichiProgressBar {
            width: parent.width
            value: root.progress * 100
            indeterminate: root.indeterminate
            accessibleName: root.title
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                text: root.statusText
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                width: root.cancelEnabled ? parent.width - cancelBtn.width - MichiTheme.spacing.sm : parent.width
                elide: Text.ElideRight
                visible: text !== ""
            }

            MichiButton {
                id: cancelBtn
                text: "Cancelar"
                variant: "ghost"
                visible: root.cancelEnabled
                onClicked: root.cancelRequested()
            }
        }
    }
}
