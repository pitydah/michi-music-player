import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

// MichiSeparator — theme-correct menu separator (Basic's default renders
// with the raw Qt palette grey, which clashes with the glass surface).
MenuSeparator {
    id: root
    padding: MichiSpacing.xxs
    contentItem: Item { }
    background: Rectangle {
        implicitWidth: 200
        implicitHeight: 1
        anchors.leftMargin: MichiSpacing.md
        anchors.rightMargin: MichiSpacing.md
        color: MichiSemanticColors.borderSubtle
    }
}
