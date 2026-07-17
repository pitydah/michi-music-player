import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Detail"
    objectName: "mixDetailPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _mixTitle: ""
    property var _songs: []
    property bool _generating: false
    property bool _cancelling: false
    property string _errorMsg: ""
    property string _state: "idle"

    signal backRequested()



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

    function explainMix() {
        if (!root.mx || typeof root.mx.explainCurrentMix !== "function") return
        var explanation = root.mx.explainCurrentMix()
        root._errorMsg = explanation && explanation.ok
            ? "Mix basado en: " + (explanation.reasons || []).join(", ")
            : "No disponible"
    }

    Flickable {
        id: flick
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        focus: true

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    Accessible.role: Accessible.Button

                    text: "Volver"; variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: detailPlayBtn
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
                visible: text !== ""
                showDismiss: true
                onDismissed: root._errorMsg = ""
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                    Accessible.role: Accessible.Button

                MichiButton {
                    id: detailPlayBtn
                    text: "Reproducir"; variant: "primary"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailEnqueueBtn
                    KeyNavigation.backtab: detailBackBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (root.mx && typeof root.mx.playMix !== "undefined")
                            root.mx.playMix()
                    }
                }

                MichiButton {
                    id: detailEnqueueBtn
                    text: "Agregar a cola"; variant: "secondary"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailRegenerateBtn
                    KeyNavigation.backtab: detailPlayBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (root.mx && typeof root.mx.enqueueMix !== "undefined")
                            root.mx.enqueueMix()
                    }
                    Accessible.role: Accessible.Button

                }

                MichiButton {
                    id: detailRegenerateBtn
                    text: {
                        if (root._state === "generating") return "Generando..."
                        if (root._state === "cancelling") return "Cancelando..."
                        return "Regenerar"
                    }
                    variant: "ghost"
                    activeFocusOnTab: true
                    enabled: !root._generating && !root._cancelling
                    KeyNavigation.tab: detailSaveBtn
                    KeyNavigation.backtab: detailEnqueueBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    Accessible.role: Accessible.Button

                    onClicked: root.generateMix()
                }

                MichiButton {
                    id: detailSaveBtn
                    text: "Guardar como playlist"; variant: "ghost"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailExplainBtn
                    KeyNavigation.backtab: detailRegenerateBtn
                    Keys.onReturnPressed: onClicked()
                    Accessible.role: Accessible.Button

                    Keys.onSpacePressed: onClicked()
                    onClicked: saveDialog.open()
                }

                MichiButton {
                    id: detailExplainBtn
                    text: "Explicar mix"; variant: "ghost"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailCancelBtn
                    KeyNavigation.backtab: detailSaveBtn
                    Accessible.role: Accessible.Button

                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.explainMix()
                }

                MichiButton {
                    id: detailCancelBtn
                    text: "Cancelar generación"; variant: "danger"
                    activeFocusOnTab: true
                    visible: root._generating
                    KeyNavigation.tab: trackListView
                    KeyNavigation.backtab: detailExplainBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.cancelGeneration()
                }
            }

            MixGenerationProgress {
                visible: root._generating || root._cancelling
                statusText: root._cancelling ? "Cancelando..." : "Generando mix..."
                cancellable: root._generating
                onCancelRequested: root.cancelGeneration()
            }

                Accessible.role: Accessible.List

                Accessible.name: "ListView"

            Text {
                text: root._songs.length + " canciones"; color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root._songs.length > 0
            }

            ListView {
                focusPolicy: Qt.StrongFocus
                id: trackListView
                width: parent.width; height: root._songs.length > 0
                    ? Math.min(root._songs.length * 44, flick.height - 220)
                    : 60
                model: root._songs; clip: true; spacing: 2
                activeFocusOnTab: true

                delegate: Rectangle {
                    width: parent.width; height: 44
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm
                    activeFocusOnTab: true
                    KeyNavigation.tab: index < root._songs.length - 1
                        ? trackListView.itemAtIndex(index + 1)
                        : detailExplainBtn
                    KeyNavigation.backtab: index > 0
                        ? trackListView.itemAtIndex(index - 1)
                        : detailCancelBtn.visible ? detailCancelBtn : detailExplainBtn

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
                    text: root._state === "cancelled"
                        ? "Generación cancelada"
                        : "Mix vacío. Selecciona un tipo de mix para generar contenido."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            MixFeedbackControls {
                width: parent.width; visible: root._songs.length > 0
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

            }
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
                focusPolicy: Qt.StrongFocus
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
