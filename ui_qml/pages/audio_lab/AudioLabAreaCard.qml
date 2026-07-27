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
    property url iconSource: ""
    property string status: "unavailable"
    property var tools: []

    signal activated(string areaKey)

    implicitHeight: 190
    implicitWidth: 320
    variant: status === "available" ? "accent" : "base"
    interactive: status !== "unavailable"
    hovered: hoverHandler.hovered
    pressed: tapHandler.pressed
    activeFocusOnTab: interactive

    Accessible.role: Accessible.Button
    Accessible.name: title + ". " + description
    Accessible.description: status === "available" ? "Disponible" : status === "partial" ? "Disponibilidad parcial" : "No disponible"
    Accessible.onPressAction: {
        if (root.interactive)
            root.activated(root.areaKey)
    }

    Keys.onReturnPressed: {
        if (root.interactive)
            root.activated(root.areaKey)
    }
    Keys.onSpacePressed: {
        if (root.interactive)
            root.activated(root.areaKey)
    }

    HoverHandler { id: hoverHandler }
    TapHandler {
        id: tapHandler
        enabled: root.interactive
        onTapped: root.activated(root.areaKey)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm

            Rectangle {
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                radius: MichiTheme.radius.md
                color: MichiTheme.colors.accentGlowSubtle
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.accentSeparator

                MichiIcon {
                    anchors.centerIn: parent
                    source: root.iconSource
                    size: MichiTheme.iconSizeLarge
                    color: root.status === "available"
                           ? MichiTheme.colors.accentPrimary
                           : MichiTheme.colors.textSecondary
                    accessibleName: ""
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
            }

            StatusBadge {
                text: root.status === "available" ? "Disponible"
                    : root.status === "partial" ? "Parcial"
                    : "No disponible"
                kind: root.status === "available" ? "success"
                    : root.status === "partial" ? "warning"
                    : "disconnected"
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.description
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
        }

        Flow {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.xs

            Repeater {
                model: root.tools || []

                StatusBadge {
                    text: modelData.name || modelData.id || "Herramienta"
                    kind: modelData.status === "available" ? "success"
                        : modelData.status === "experimental" ? "warning"
                        : modelData.status === "missing_dependency" ? "disconnected"
                        : "info"
                }
            }
        }

        Item { Layout.fillHeight: true }

        Row {
            Layout.alignment: Qt.AlignRight
            spacing: MichiTheme.spacing.xs

            Text {
                text: root.interactive ? qsTr("Abrir") : qsTr("Dependencia pendiente")
                color: root.interactive ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightMedium
            }

            MichiIcon {
                source: "../../../icons/actions/chevron-right.svg"
                size: MichiTheme.iconSizeSmall
                color: MichiTheme.colors.accentBlue
                visible: root.interactive
                accessibleName: ""
            }
        }
    }
}
