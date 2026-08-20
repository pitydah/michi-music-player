import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

RowLayout {
    id: root
    property string title: ""
    property string subtitle: ""
    property color accentColor: MichiPalette.auroraBlue
    default property alias actions: actionHost.data
    spacing: MichiSpacing.md
    Rectangle {
        Layout.preferredWidth: 2
        Layout.preferredHeight: 34
        radius: 1
        gradient: Gradient {
            GradientStop { position: 0; color: root.accentColor }
            GradientStop { position: 1; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16) }
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.xxs
        MichiText { Layout.fillWidth: true; text: root.title; role: "title"; elide: Text.ElideRight }
        MichiText { Layout.fillWidth: true; text: root.subtitle; role: "secondary"; visible: text.length > 0; elide: Text.ElideRight }
    }
    RowLayout { id: actionHost; spacing: MichiSpacing.sm }
}
