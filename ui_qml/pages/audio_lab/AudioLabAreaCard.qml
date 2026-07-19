import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

GlassMaterial {
    id: root

    property string areaKey: ""
    property string title: ""
    property string description: ""
    property string iconText: ""
    property string status: "unavailable"
    property var tools: []

    signal activated(string areaKey)

    implicitHeight: 190
    implicitWidth: 320
    variant: status === "available" ? "accent" : "base"
    interactive: status !== "unavailable"
    activeFocusOnTab: interactive

    Accessible.role: Accessible.Button
    Accessible.name: title
    Accessible.description: description || qsTr("Área de Audio Lab")

    HoverHandler { id: hoverHandler }
    TapHandler { id: tapHandler; onTapped: if (interactive) root.activated(areaKey) }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm

            Label {
                text: root.iconText || "♪"
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                color: MichiTheme.colors.textPrimary
            }

            Label {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: Font.DemiBold
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            StatusBadge {
                text: root.status === "available" ? qsTr("Disponible")
                      : root.status === "partial" ? qsTr("Parcial") : qsTr("No disponible")
                kind: root.status === "available" ? "success"
                      : root.status === "partial" ? "warning" : "info"
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.description
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }
    }

    Keys.onReturnPressed: if (interactive) root.activated(areaKey)
    Keys.onSpacePressed: if (interactive) root.activated(areaKey)
}
