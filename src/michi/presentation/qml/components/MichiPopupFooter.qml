import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

// Shared F11 footer: fixed actions, visually distinct from destructive intent.
ColumnLayout {
    id: root
    default property alias contentData: actionRow.data
    property string note: ""

    Layout.fillWidth: true
    spacing: MichiSpacing.sm

    MichiDivider { Layout.fillWidth: true }

    RowLayout {
        Layout.fillWidth: true
        Layout.minimumHeight: 32
        spacing: MichiSpacing.sm

        MichiText {
            visible: root.note !== ""
            text: root.note
            role: "caption"
            color: MichiPalette.textSecondary
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        Item { Layout.fillWidth: root.note === "" }

        RowLayout {
            id: actionRow
            spacing: MichiSpacing.sm
        }
    }
}
