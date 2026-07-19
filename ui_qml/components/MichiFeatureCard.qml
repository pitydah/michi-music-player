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

    accessibleName: featureAccessibleName
    accessibleDescription: description
    subtitle: description
    elevated: emphasis === "high"

    RowLayout {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        MichiIcon {
            iconKey: root.iconKey
            size: 24
            active: root.emphasis === "high"
            accessibleName: root.title
        }

        Item { Layout.fillWidth: true }

        StatusBadge {
            visible: root.status !== "functional" && root.statusText !== ""
            text: root.statusText
            kind: root.status === "experimental" ? "experimental"
                  : root.status === "configuration_required" ? "warning"
                  : "info"
        }
    }
}
