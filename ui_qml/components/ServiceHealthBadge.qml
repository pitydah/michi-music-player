import QtQuick
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    objectName: "serviceHealthBadge"
    focus: false
    id: root

    enum Health {
        HEALTHY,
        DEGRADED,
        UNAVAILABLE
    }

    property int health: ServiceHealthBadge.HEALTHY
    property string serviceName: ""
    property string healthyLabel: "Saludable"
    property string degradedLabel: "Degradado"
    property string unavailableLabel: "No disponible"
    property bool showPulse: false

    Accessible.name: root.health === ServiceHealthBadge.DEGRADED ? root.serviceName + " " + root.degradedLabel :
                     root.health === ServiceHealthBadge.UNAVAILABLE ? root.serviceName + " " + root.unavailableLabel :
                     root.serviceName + " " + root.healthyLabel
    Accessible.description: "Estado del servicio" + (serviceName ? ": " + serviceName : "")

    implicitHeight: 22
    implicitWidth: badgeRow.implicitWidth + MichiTheme.spacing.md * 2
    radius: MichiTheme.radius.pill
    color: {
        switch (root.health) {
            case ServiceHealthBadge.HEALTHY: return MichiTheme.colors.badgeActiveBg
            case ServiceHealthBadge.DEGRADED: return MichiTheme.colors.badgeWarningBg
            case ServiceHealthBadge.UNAVAILABLE: return MichiTheme.colors.badgeDangerBg
        }
        return MichiTheme.colors.badgeMutedBg
    }
    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderInner

    Row {
        id: badgeRow
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.xs

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 6
            height: 6
            radius: width / 2
            color: {
                switch (root.health) {
                    case ServiceHealthBadge.HEALTHY: return MichiTheme.colors.success
                    case ServiceHealthBadge.DEGRADED: return MichiTheme.colors.warning
                    case ServiceHealthBadge.UNAVAILABLE: return MichiTheme.colors.error
                }
                return MichiTheme.colors.disconnected
            }

            SequentialAnimation on opacity {
                running: root.showPulse && root.health === ServiceHealthBadge.DEGRADED
                loops: Animation.Infinite
                NumberAnimation { from: 0.5; to: 1.0; duration: 800 }
                NumberAnimation { from: 1.0; to: 0.5; duration: 800 }
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: {
                switch (root.health) {
                    case ServiceHealthBadge.HEALTHY: return root.healthyLabel
                    case ServiceHealthBadge.DEGRADED: return root.degradedLabel
                    case ServiceHealthBadge.UNAVAILABLE: return root.unavailableLabel
                }
                return ""
            }
            color: {
                switch (root.health) {
                    case ServiceHealthBadge.HEALTHY: return MichiTheme.colors.badgeActiveText
                    case ServiceHealthBadge.DEGRADED: return MichiTheme.colors.warning
                    case ServiceHealthBadge.UNAVAILABLE: return MichiTheme.colors.error
                }
                return MichiTheme.colors.textMuted
            }
            font.pixelSize: MichiTheme.typography.badgeSize
            font.weight: MichiTheme.typography.weightMedium
        }
    }
}
