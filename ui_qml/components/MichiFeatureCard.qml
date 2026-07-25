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
            visible: root.status !== "functional" && root.statusText !== ""
            text: root.statusText
            kind: root.status === "experimental" ? "experimental"
                  : root.status === "configuration_required" ? "warning"
                  : "info"
        }
    }
}
