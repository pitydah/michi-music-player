import QtQuick
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    objectName: "connectionStatusBadge"
    focus: false
    id: root

    enum Status {
        CONNECTED,
        DISCONNECTED,
        RECONNECTING
    }

    property int status: ConnectionStatusBadge.DISCONNECTED
    property string connectedLabel: "Conectado"
    property string disconnectedLabel: "Desconectado"
    property string reconnectingLabel: "Reconectando\u2026"
    property string serviceName: ""

    Accessible.name: root.status === ConnectionStatusBadge.CONNECTED ? root.connectedLabel :
                     root.status === ConnectionStatusBadge.DISCONNECTED ? root.disconnectedLabel :
                     root.status === ConnectionStatusBadge.RECONNECTING ? root.reconnectingLabel :
                     root.disconnectedLabel
    Accessible.description: (serviceName ? serviceName + ": " : "") + Accessible.name

    implicitHeight: 22
    implicitWidth: badgeRow.implicitWidth + MichiTheme.spacing.md * 2
    radius: MichiTheme.radiusPill
    color: {
        switch (root.status) {
            case ConnectionStatusBadge.CONNECTED: return MichiTheme.colors.badgeActiveBg
            case ConnectionStatusBadge.DISCONNECTED: return MichiTheme.colors.badgeMutedBg
            case ConnectionStatusBadge.RECONNECTING: return MichiTheme.colors.badgeWarningBg
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
                switch (root.status) {
                    case ConnectionStatusBadge.CONNECTED: return MichiTheme.colors.success
                    case ConnectionStatusBadge.DISCONNECTED: return MichiTheme.colors.disconnected
                    case ConnectionStatusBadge.RECONNECTING: return MichiTheme.colors.warning
                }
                return MichiTheme.colors.disconnected
            }

            SequentialAnimation on opacity {
                running: root.status === ConnectionStatusBadge.RECONNECTING
                loops: Animation.Infinite
                NumberAnimation { from: 0.4; to: 1.0; duration: 600 }
                NumberAnimation { from: 1.0; to: 0.4; duration: 600 }
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: {
                switch (root.status) {
                    case ConnectionStatusBadge.CONNECTED: return root.connectedLabel
                    case ConnectionStatusBadge.DISCONNECTED: return root.disconnectedLabel
                    case ConnectionStatusBadge.RECONNECTING: return root.reconnectingLabel
                }
                return ""
            }
            color: {
                switch (root.status) {
                    case ConnectionStatusBadge.CONNECTED: return MichiTheme.colors.badgeActiveText
                    case ConnectionStatusBadge.DISCONNECTED: return MichiTheme.colors.disconnected
                    case ConnectionStatusBadge.RECONNECTING: return MichiTheme.colors.warning
                }
                return MichiTheme.colors.textMuted
            }
            font.pixelSize: MichiTheme.typography.badgeSize
            font.weight: MichiTheme.typography.weightMedium
        }
    }
}
