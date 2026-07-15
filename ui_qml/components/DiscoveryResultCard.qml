import QtQuick
import "../theme"
import "../materials"

Item {
    id: root

    property string serverName: ""
    property string serverHost: ""
    property string serverType: ""
    property string serverStatus: "disconnected"
    property string ctaText: "Conectar"

    signal ctaClicked()

    GlassMaterial {
        anchors.fill: parent
        variant: "base"
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radiusMd

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.serverName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                    width: parent.width - 100
                }

                StatusBadge {
                    text: {
                        switch (root.serverStatus) {
                            case "connected": return "Conectado"
                            case "detected": return "Detectado"
                            default: return "Desconectado"
                        }
                    }
                    kind: {
                        switch (root.serverStatus) {
                            case "connected": return "success"
                            case "detected": return "info"
                            default: return "disconnected"
                        }
                    }
                }
            }

            Text {
                text: root.serverHost
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.serverHost !== ""
            }

            Text {
                text: root.serverType
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.serverType !== ""
            }

            MichiButton {
                text: root.ctaText
                variant: "secondary"
                onClicked: root.ctaClicked()
            }
        }
    }
}
