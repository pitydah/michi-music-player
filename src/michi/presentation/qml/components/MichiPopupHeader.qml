import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

// Shared F11 popup header: one title, one subtitle, one honest state.
ColumnLayout {
    id: root
    property string iconName: ""
    property string title: ""
    property string subtitle: ""
    property string badgeText: ""
    property string badgeTone: "neutral"
    property alias trailingData: trailingSlot.data

    Layout.fillWidth: true
    spacing: MichiSpacing.sm

    RowLayout {
        Layout.fillWidth: true
        Layout.minimumHeight: 48
        spacing: MichiSpacing.md

        MichiIcon {
            visible: root.iconName !== ""
            name: root.iconName
            width: MichiMetrics.iconMedium
            height: width
            iconColor: MichiPalette.auroraCyan
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            MichiText {
                text: root.title
                role: "section"
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            MichiText {
                visible: root.subtitle !== ""
                text: root.subtitle
                role: "caption"
                color: MichiPalette.textSecondary
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }

        MichiStatusChip {
            visible: root.badgeText !== ""
            text: root.badgeText
            tone: root.badgeTone
            dotVisible: false
        }

        RowLayout {
            id: trailingSlot
            spacing: MichiSpacing.xs
        }
    }

    MichiDivider { Layout.fillWidth: true }
}
