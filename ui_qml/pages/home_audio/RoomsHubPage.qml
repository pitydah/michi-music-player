import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "roomsHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Habitaciones y zonas"

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: qsTr("Habitaciones y zonas")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Gestiona zonas de audio multiroom y agrupa dispositivos por habitacion.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            StatusBadge {
                text: qsTr("Parcial")
                kind: "warning"
            }

            Text {
                text: qsTr("La configuracion multiroom requiere dispositivos compatibles con Snapcast o Michi Music Stream.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            SectionHeader {
                text: qsTr("Zonas configuradas")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: parent.width > 900 ? 3 : 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.ha && root.ha.zones ? root.ha.zones : []

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 80
                        title: modelData.name || qsTr("Zona")
                        subtitle: (modelData.devices ? modelData.devices.length : 0) + " dispositivo(s)"
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge && modelData.id)
                                navigationBridge.navigateWithParams("zone_detail", {zoneId: modelData.id})
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: modelData.state || modelData.status || qsTr("idle")
                            kind: modelData.state === "playing" ? "active" : "info"
                        }
                    }
                }

                Text {
                    text: qsTr("No hay zonas configuradas. Agrega dispositivos desde Conexiones para comenzar.")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                    visible: !root.ha || !root.ha.zones || root.ha.zones.length === 0
                }
            }
        }
    }
}
