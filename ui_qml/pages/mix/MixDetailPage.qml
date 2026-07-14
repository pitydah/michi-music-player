import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _mixTitle: ""
    property var _songs: []
    property bool _generating: false
    property string _errorMsg: ""

    signal backRequested()

    function refresh() {
        if (root.mx) {
            root._mixTitle = root.mx.currentMixTitle || ""
            root._songs = root.mx.currentSongs || []
            root._errorMsg = root.mx.errorMessage || ""
        }
    }

    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.lg

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width
            MichiButton { text: "Volver"; variant: "ghost"; onClicked: root.backRequested() }

            Text {
                text: root._mixTitle; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: MichiTheme.spacing.md }

            MichiButton {
                text: "Reproducir"; variant: "primary"
                onClicked: {
                    if (root.mx && typeof root.mx.playMix !== "undefined")
                        root.mx.playMix()
                }
            }
            MichiButton {
                text: "Agregar a cola"; variant: "secondary"
                onClicked: {
                    if (root.mx && typeof root.mx.enqueueMix !== "undefined")
                        root.mx.enqueueMix()
                }
            }
            MichiButton {
                text: root._generating ? "Generando..." : "Regenerar"
                variant: "ghost"; enabled: !root._generating
                onClicked: {
                    if (root.mx && typeof root.mx.refresh !== "undefined") {
                        root._generating = true
                        root.mx.refresh()
                        root._generating = false
                        root.refresh()
                    }
                }
            }
            MichiButton {
                text: "Guardar como playlist"; variant: "ghost"
                onClicked: saveDialog.open()
            }
            MichiButton {
                text: "Explicar mix"; variant: "ghost"
                onClicked: {
                    if (root.mx && typeof root.mx.explainCurrentMix !== "undefined") {
                        var explanation = root.mx.explainCurrentMix()
                        root._errorMsg = explanation && explanation.ok
                            ? "Mix basado en: " + (explanation.reasons || []).join(", ")
                            : "No disponible"
                    }
                }
            }
            MichiButton {
                text: "Cancelar generación"; variant: "danger"
                visible: root._generating
                onClicked: {
                    if (root.mx && typeof root.mx.cancelGeneration !== "undefined")
                        root.mx.cancelGeneration()
                    root._generating = false
                }
            }
        }

        Text {
            text: root._errorMsg; color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.bodySize; visible: text !== ""
            width: parent.width; wrapMode: Text.WordWrap
        }

        MixGenerationProgress { visible: root._generating }

        Text {
            text: root._songs.length + " canciones"; color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._songs.length > 0
        }

        ListView {
            width: parent.width; height: parent.height - 180
            model: root._songs; clip: true; spacing: 1

            delegate: Rectangle {
                width: parent.width; height: 40
                color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                radius: MichiTheme.radiusSm

                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    Text {
                        width: parent.width * 0.40; text: modelData.title || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.25; text: modelData.artist || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.15; text: modelData.album || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 30; text: modelData.reason || ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 24; text: "▶"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                                    root.mx.playFromIndex(index)
                            }
                        }
                    }
                }

                MouseArea {
                    id: mouseArea; anchors.fill: parent; hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }

            Text {
                anchors.centerIn: parent; visible: parent.count === 0
                text: "Mix vacío. Selecciona un tipo de mix para generar contenido."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
            }
        }

        MixFeedbackControls {
            width: parent.width; visible: root._songs.length > 0
        }
    }

    Dialog {
        id: saveDialog; title: "Guardar mix como playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel; modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3
        Column {
            spacing: MichiTheme.spacing.md
            Text { text: "Nombre de la playlist:"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                id: saveName; width: 280; text: root._mixTitle
                placeholderText: "Nombre de la playlist"
            }
        }
        onAccepted: {
            var name = saveName.text.trim()
            if (name && root.mx && typeof root.mx.saveMixAsPlaylist !== "undefined")
                root.mx.saveMixAsPlaylist(name)
        }
    }

    Component.onCompleted: root.refresh()
}
