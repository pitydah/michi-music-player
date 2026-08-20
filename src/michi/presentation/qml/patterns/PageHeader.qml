import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

RowLayout {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias actions: actionHost.data
    spacing: MichiSpacing.md
    ColumnLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.xxs
        MichiText { Layout.fillWidth: true; text: root.title; role: "title"; elide: Text.ElideRight }
        MichiText { Layout.fillWidth: true; text: root.subtitle; role: "secondary"; visible: text.length > 0; elide: Text.ElideRight }
    }
    RowLayout { id: actionHost; spacing: MichiSpacing.sm }
}
