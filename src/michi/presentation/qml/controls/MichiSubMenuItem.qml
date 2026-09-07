import QtQuick
import QtQuick.Controls.Basic
import "../controls"
import "../theme"

// MichiSubMenuItem (R10 — Context Menu System V2): item con submenú real.
// La jerarquía de los menús premium deja de ser plana: las familias de
// acciones viven en submenús (V4 §37-42: Columns >, Preset >, etc.).
MenuItem {
    id: root

    property string label: ""
    property string icon: ""
    property Menu subMenuRef: null

    text: root.label
    icon.name: root.icon || ""
    subMenu: root.subMenuRef

    contentItem: RowLayout {
        spacing: MichiSpacing.sm
        MichiText {
            text: root.label
            role: "primary"
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.leftMargin: MichiSpacing.sm + 2
        }
        // Chevron discreto del submenú (jerarquía visible).
        MichiText {
            text: qsTr("›")
            role: "caption"
            color: MichiPalette.textMuted
            Layout.rightMargin: MichiSpacing.xs
        }
    }
}
