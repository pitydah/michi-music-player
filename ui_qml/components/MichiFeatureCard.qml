import QtQuick
import QtQuick.Layouts
import "../theme"

MichiCard {
    id: root

    property string description: ""
    property string iconKey: ""
    property string status: "functional"
    property string statusText: ""
    property string route: ""
    property string primaryActionText: ""
    property string emphasis: "normal"
    property var metadata: ({})
    property string capability: ""
    property bool capabilityAvailable: true
    property string metadataText: ""
    property string featureAccessibleName: title

    interactive: true
    accessibleName: featureAccessibleName
    accessibleDescription: description
    subtitle: description
    elevated: emphasis === "high"
    variant: status === "experimental" ? "accent"
             : status === "configuration_required" || status === "dependency_missing"
               || status === "hardware_validation_pending" ? "warning"
             : status === "partial" || status === "planned" ? "info"
             : status === "error" || status === "failure" ? "danger"
             : emphasis === "high" ? "elevated" : "solid"

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.xs

        RowLayout {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiIcon {
                iconKey: root.iconKey
                size: 20
                active: root.emphasis === "high"
                accessibleName: root.title
            }

            Text {
                Layout.fillWidth: true
                visible: root.primaryActionText !== ""
                text: root.primaryActionText
                color: MichiTheme.colors.accentPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
            }

            StatusBadge {
                visible: root.capability !== ""
                text: root.capability
                kind: root.capabilityAvailable ? "info" : "warning"
                maximumWidth: 140
            }

            StatusBadge {
                visible: root.statusText !== ""
                text: root.statusText
                kind: root.status === "experimental" ? "experimental"
                      : root.status === "configuration_required" ? "warning"
                      : root.status === "functional" ? "success"
                      : "info"
            }
        }

        Text {
            width: parent.width
            visible: root.metadataText !== ""
            text: root.metadataText
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
        }
    }
}
