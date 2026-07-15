import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _mixParams: ({})
    property var _trackExplanations: []
    property bool _open: false

    signal closed()

    objectName: "MixExplanationDrawer"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Explicación del Mix"

    function show(mixParams, trackExplanations) {
        root._mixParams = mixParams || {}
        root._trackExplanations = trackExplanations || []
        root._open = true
    }

    function dismiss() {
        root._open = false
        root.closed()
    }

    function loadExplanation() {
        if (root.mx && typeof root.mx.explainCurrentMix === "function") {
            var result = root.mx.explainCurrentMix()
            if (result && result.ok) {
                root._mixParams = { reasons: result.reasons || [], total: result.total || 0 }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        visible: root._open
        opacity: root._open ? 1.0 : 0.0
        z: 10

        Behavior on opacity { NumberAnimation { duration: MichiTheme.motion.normal } }

        MouseArea {
            anchors.fill: parent
            onClicked: root.dismiss()
        }

        Rectangle {
            id: drawerPanel
            width: parent.width * 0.40
            height: parent.height
            anchors.right: parent.right
            color: MichiTheme.colors.surfaceCardElevated
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
            radius: 0

            Column {
                anchors.fill: parent; spacing: MichiTheme.spacing.md

                Rectangle {
                    width: parent.width; height: 48
                    color: "transparent"

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Explicación del Mix"; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { width: parent.width - dismissBtn.width - MichiTheme.spacing.lg - 60; height: 1 }

                        Text {
                            id: dismissBtn
                            text: "[X] Cerrar"; color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                            objectName: "explanationDrawerDismissBtn"
                            Accessible.name: "Cerrar explicación"
                            activeFocusOnTab: true

                            Keys.onReturnPressed: root.dismiss()
                            Keys.onSpacePressed: root.dismiss()
                            Keys.onEscapePressed: root.dismiss()

                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: root.dismiss()
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Flickable {
                    width: parent.width; height: parent.height - 100
                    contentHeight: contentCol.height + MichiTheme.spacing.xl
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    activeFocusOnTab: true

                    Column {
                        id: contentCol
                        width: parent.width - MichiTheme.spacing.xl * 2
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiTheme.spacing.lg

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Parámetros del Mix"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                            }

                            Repeater {
                                model: {
                                    var keys = Object.keys(root._mixParams)
                                    var items = []
                                    for (var i = 0; i < keys.length; i++) {
                                        var v = root._mixParams[keys[i]]
                                        if (Array.isArray(v)) {
                                            if (v.length > 0) items.push({ key: keys[i], value: v.join(", ") })
                                        } else if (typeof v === "boolean") {
                                            items.push({ key: keys[i], value: v ? "Sí" : "No" })
                                        } else if (v !== null && v !== undefined) {
                                            items.push({ key: keys[i], value: String(v) })
                                        }
                                    }
                                    return items
                                }

                                delegate: Row {
                                    width: parent.width; spacing: MichiTheme.spacing.sm
                                    Text {
                                        width: parent.width * 0.35
                                        text: modelData.key; color: MichiTheme.colors.textSecondary
                                        font.pixelSize: MichiTheme.typography.metaSize
                                    }
                                    Text {
                                        width: parent.width * 0.60
                                        text: modelData.value; color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            Text {
                                text: root._trackExplanations.length === 0
                                    ? (root._mixParams.reasons ? "Razones: " + root._mixParams.reasons.join(", ") : "Sin parámetros disponibles")
                                    : ""
                                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                                wrapMode: Text.WordWrap; width: parent.width
                                visible: text !== ""
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Reglas aplicadas por canción"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                                visible: root._trackExplanations.length > 0
                            }

                            Repeater {
                                model: root._trackExplanations

                                delegate: Rectangle {
                                    width: parent.width; height: 48
                                    color: MichiTheme.colors.surfaceCard
                                    radius: MichiTheme.radiusSm
                                    border.width: MichiTheme.borderWidth
                                    border.color: MichiTheme.colors.borderSubtle

                                    Row {
                                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                                        Text {
                                            width: parent.width * 0.40; text: modelData.title || ""
                                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                        }

                                        Text {
                                            width: parent.width * 0.50; text: modelData.reason || ""
                                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                            wrapMode: Text.WordWrap; anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Keys.onEscapePressed: {
        if (root._open) root.dismiss()
    }
}
