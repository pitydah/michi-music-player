import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    objectName: "mixDetail.page"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _mixTitle: ""
    property var _songs: []
    property bool _generating: false
    property bool _cancelling: false
    property string _errorMsg: ""
    property string _state: "idle"

    signal backRequested()

    objectName: "MixDetailPage"

    Accessible.role: Accessible.Pane
    Accessible.name: _mixTitle || "Mix"

    function refresh() {
        if (root.mx) {
            root._mixTitle = root.mx.currentMixTitle || ""
            root._songs = root.mx.currentSongs || []
            root._errorMsg = root.mx.errorMessage || ""
            root._state = root._songs.length > 0 ? "ready" : "idle"
        }
    }

    function generateMix() {
        if (!root.mx) {
            root._errorMsg = "Servicio de mix no disponible"
            root._state = "failed"
            return
        }
        root._state = "generating"
        root._generating = true
        root._cancelling = false
        root._errorMsg = ""

        var result = root.mx.refresh()
        if (result && result.ok) {
            root.refresh()
        }
        root._generating = false
        root._state = root._songs.length > 0 ? "ready" : "no_candidates"
    }

    function cancelGeneration() {
        if (!root.mx || !root._generating) return
        root._state = "cancelling"
        root._cancelling = true
        root._errorMsg = ""

        var result = root.mx.cancelGeneration()
        if (result && result.ok) {
            root._generating = false
            root._cancelling = false
            root._state = "cancelled"
            root._errorMsg = "Generación cancelada"
        }
    }

    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.lg

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width

            MichiButton {
                text: "Volver"; variant: "ghost"
                objectName: "detailBackBtn"
                Accessible.name: "Volver"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.backRequested()
            }

            Text {
                text: root._mixTitle; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        InlineError {
            width: parent.width
            message: root._errorMsg
            visible: root._errorMsg !== ""
            showDismiss: true
            onDismissed: root._errorMsg = ""
        }

        Row {
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Reproducir"; variant: "primary"
                objectName: "detailPlayBtn"
                Accessible.name: "Reproducir mix"
                activeFocusOnTab: true
                enabled: root._songs.length > 0
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root.mx && typeof root.mx.playMix !== "undefined")
                        root.mx.playMix()
                }
            }
            MichiButton {
                text: "Agregar a cola"; variant: "secondary"
                objectName: "detailEnqueueBtn"
                Accessible.name: "Agregar mix a la cola"
                activeFocusOnTab: true
                enabled: root._songs.length > 0
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root.mx && typeof root.mx.enqueueMix !== "undefined")
                        root.mx.enqueueMix()
                }
            }
            MichiButton {
                text: root._generating ? "Generando..." : "Regenerar"
                variant: "ghost"; enabled: !root._generating && !root._cancelling
                objectName: "detailRegenerateBtn"
                Accessible.name: "Regenerar mix"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.generateMix()
            }
            MichiButton {
                text: "Guardar como playlist"; variant: "ghost"
                objectName: "detailSaveBtn"
                Accessible.name: "Guardar mix como playlist"
                activeFocusOnTab: true
                enabled: root._songs.length > 0
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: saveDialog.open()
            }
            MichiButton {
                text: "Explicar mix"; variant: "ghost"
                objectName: "detailExplainBtn"
                Accessible.name: "Explicar mix"
                activeFocusOnTab: true
                enabled: root._songs.length > 0
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
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
                objectName: "detailCancelBtn"
                Accessible.name: "Cancelar generación"
                activeFocusOnTab: true
                visible: root._generating
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.cancelGeneration()
            }
        }

        MixGenerationProgress { visible: root._generating || root._cancelling }

        ListView {
            width: parent.width; height: parent.height - 200
            model: root._songs; clip: true; spacing: 2
            activeFocusOnTab: true
            objectName: "mixTrackListView"
            Accessible.name: "Canciones del mix"

            delegate: Rectangle {
                width: parent.width; height: 44
                color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                radius: MichiTheme.radiusSm
                activeFocusOnTab: true
                objectName: "mixTrackItem_" + index
                Accessible.name: modelData.title + " - " + modelData.artist
                KeyNavigation.tab: index < root._songs.length - 1
                    ? trackListView.itemAtIndex(index + 1)
                    : null
                KeyNavigation.backtab: index > 0
                    ? trackListView.itemAtIndex(index - 1)
                    : null
                Keys.onReturnPressed: {
                    if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                        root.mx.playFromIndex(index)
                }
                Keys.onSpacePressed: {
                    if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                        root.mx.playFromIndex(index)
                }

                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    Text {
                        width: parent.width * 0.35; text: modelData.title || ""
                        color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.22; text: modelData.artist || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: parent.width * 0.18; text: modelData.album || ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 30; text: modelData.reason || ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        width: 24; text: "P"; color: MichiTheme.colors.accentBlue
                        font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                                    root.mx.playFromIndex(index)
                            }
                        }
                    }
                    Text {
                        width: 24; text: "+"; color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.cardTitleSize; anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.mx && typeof root.mx.enqueueTrack !== "undefined")
                                    root.mx.enqueueTrack(index)
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
