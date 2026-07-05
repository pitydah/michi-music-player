import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var stg: typeof settingsBridge !== "undefined" ? settingsBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _activeProfile: root.stg ? root.stg.getActiveProfile() : ""

    function refreshActive() {
        _activeProfile = root.stg ? root.stg.getActiveProfile() : ""
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Perfiles de salida"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Selecciona el perfil de audio que mejor se adapte a tu equipo y tipo de archivo."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: root.stg ? root.stg.outputProfiles : []

                GlassCard {
                    width: parent.width
                    height: 100
                    title: modelData.name || ""
                    subtitle: modelData.description || ""
                    variant: modelData.key === root._activeProfile ? "accent" : "base"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.xs

                        Text {
                            Layout.fillWidth: true
                            text: modelData.name || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: modelData.key === root._activeProfile ? FontWeight.Medium : FontWeight.Normal
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.description || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        RowLayout {
                            spacing: MichiTheme.spacing.xs
                            visible: modelData.dsd_mode || modelData.bitperfect || modelData.preferred_backend

                            StatusBadge {
                                text: "DSD: " + modelData.dsd_mode
                                kind: "experimental"
                                visible: modelData.dsd_mode && modelData.dsd_mode !== ""
                            }

                            StatusBadge {
                                text: "Bit-Perfect"
                                kind: "success"
                                visible: modelData.bitperfect
                            }

                            StatusBadge {
                                text: modelData.preferred_backend || ""
                                kind: "info"
                                visible: modelData.preferred_backend && modelData.preferred_backend !== "auto"
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.stg && typeof root.stg.setActiveProfile === "function") {
                                var result = root.stg.setActiveProfile(modelData.key)
                                if (result && result.ok) {
                                    root._activeProfile = modelData.key
                                    if (root.notif)
                                        root.notif.showMessage("Perfil activado: " + modelData.name, "success")
                                } else if (result && !result.ok && root.notif) {
                                    root.notif.showMessage("Error: " + (result.error || "desconocido"), "error")
                                }
                            }
                        }
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Los cambios aplican a la siguiente reproducción"; kind: "info" }
                    StatusBadge { text: "Experimental — QML"; kind: "experimental" }
                }
            }
        }
    }
}
