import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Mix Detail")
    objectName: "mixDetailPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property string _mixTitle: ""
    property var _songs: []
    property bool _generating: false
    property bool _cancelling: false
    property bool _waiting: false
    property string _errorMsg: ""
    property string _state: "idle"

    signal backRequested()

    Connections {
        target: root.mx
        function onStateChanged(state) {
            if (!root._waiting) return
            if (state === "COMPLETED_WITH_TRACKS" || state === "PARTIAL_RECOMMENDATION") {
                root._waiting = false
                root._generating = false
                root._cancelling = false
                root.refresh()
            } else if (state === "CANCELLED") {
                root._waiting = false
                root._generating = false
                root._cancelling = false
                root._state = "cancelled"
                root._errorMsg = qsTr("Generación cancelada")
            } else {
                root._waiting = false
                root._generating = false
                root._cancelling = false
                root._state = "no_candidates"
                root._errorMsg = root.mx.errorMessage || ""
            }
        }
    }

    function routeEnter(route, params) {
        if (params) {
            var mixId = params.mix_id !== undefined ? String(params.mix_id) : ""
            if (mixId !== "" && root.mx && typeof root.mx.loadMix === "function") {
                var current = root.mx.currentMixId || ""
                if (current !== mixId) {
                    var res = root.mx.loadMix(mixId)
                    if (res && !res.ok) {
                        root._errorMsg = res.error || qsTr("No se pudo cargar el mix")
                        root._state = "failed"
                        return
                    }
                    if (!root.mx.currentSongs || root.mx.currentSongs.length === 0) {
                        root._generating = true
                        root._waiting = true
                        root._state = "generating"
                        return
                    }
                } else {
                    root.refresh()
                    if ((!root.mx.currentSongs || root.mx.currentSongs.length === 0)
                            && (root.mx.stateName === "QUEUED" || root.mx.stateName === "RUNNING")) {
                        root._generating = true
                        root._waiting = true
                        root._state = "generating"
                        return
                    }
                }
            }
        }
        root.refresh()
    }

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
            root._errorMsg = qsTr("Servicio de mix no disponible")
            root._state = "failed"
            return
        }
        root._state = "generating"
        root._generating = true
        root._cancelling = false
        root._waiting = false
        root._errorMsg = ""

        var result = root.mx.refresh()
        if (result && result.ok) {
            if (root.mx.currentSongs && root.mx.currentSongs.length > 0) {
                root._generating = false
                root.refresh()
            } else {
                root._waiting = true
            }
        } else {
            root._generating = false
            root._state = "no_candidates"
        }
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
            root._errorMsg = qsTr("Generación cancelada")
        }
    }

    function explainMix() {
        if (!root.mx || typeof root.mx.explainCurrentMix !== "function") return
        var explanation = root.mx.explainCurrentMix()
        root._errorMsg = explanation && explanation.ok
            ? qsTr("Mix basado en: ") + (explanation.reasons || []).join(", ")
            : qsTr("No disponible")
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
                    id: detailBackBtn

                    text: qsTr("Volver"); variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: detailPlayBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        root.backRequested()
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }
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

                MichiButton {
                    id: detailPlayBtn
                    text: qsTr("Reproducir"); variant: "primary"
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
                    text: qsTr("Agregar a cola"); variant: "secondary"
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
                }

                MichiButton {
                    id: detailRegenerateBtn
                    text: {
                        if (root._state === "generating") return qsTr("Generando...")
                        if (root._state === "cancelling") return qsTr("Cancelando...")
                        return qsTr("Regenerar")
                    }
                    variant: "ghost"
                    activeFocusOnTab: true
                    enabled: !root._generating && !root._cancelling
                    KeyNavigation.tab: detailSaveBtn
                    KeyNavigation.backtab: detailEnqueueBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()

                    onClicked: root.generateMix()
                }

                MichiButton {
                    id: detailSaveBtn
                    text: qsTr("Guardar como playlist"); variant: "ghost"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailExplainBtn
                    KeyNavigation.backtab: detailRegenerateBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: saveDialog.open()
                }

                MichiButton {
                    id: detailExplainBtn
                    text: qsTr("Explicar mix"); variant: "ghost"
                    activeFocusOnTab: true
                    enabled: root._songs.length > 0
                    KeyNavigation.tab: detailCancelBtn
                    KeyNavigation.backtab: detailSaveBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.explainMix()
                }

                MichiButton {
                    id: detailCancelBtn
                    text: qsTr("Cancelar generación"); variant: "danger"
                    activeFocusOnTab: true
                    visible: root._generating
                    KeyNavigation.tab: trackListView
                    KeyNavigation.backtab: detailExplainBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: confirmCancelDialog.open()
                }
            }

            MixGenerationProgress {
                visible: root._generating || root._cancelling
                statusText: root._cancelling ? qsTr("Cancelando...") : qsTr("Generando mix...")
                cancellable: root._generating
                onCancelRequested: confirmCancelDialog.open()
            }

            Text {
                text: qsTr("%1 canciones").arg(root._songs.length); color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root._songs.length > 0
            }

            ListView {
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.List
                Accessible.name: qsTr("Canciones del mix")
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

                        MichiIcon {
                            width: 24; height: 24
                            source: "../../../icons/sidebar/play.svg"
                            color: MichiTheme.colors.accentBlue
                            anchors.verticalCenter: parent.verticalCenter
                            accessibleName: qsTr("Reproducir")
                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                                        root.mx.playFromIndex(index)
                                }
                            }
                        }

                        MichiIcon {
                            width: 24; height: 24
                            source: "../../../icons/actions/plus.svg"
                            color: MichiTheme.colors.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                            accessibleName: qsTr("Agregar a cola")
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
                        ? qsTr("Generación cancelada")
                        : qsTr("Mix vacío. Selecciona un tipo de mix para generar contenido.")
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            MixFeedbackControls {
                width: parent.width; visible: root._songs.length > 0
                activeFocusOnTab: true
            }
        }
    }

    Dialog {
        id: confirmCancelDialog
        title: qsTr("Cancelar generación")
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Text {
            text: qsTr("¿Cancelar la generación del mix? Se perderá el progreso actual.")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap; width: 320
        }

        onAccepted: root.cancelGeneration()
    }

    Dialog {
        id: saveDialog; title: qsTr("Guardar mix como playlist")
        standardButtons: Dialog.Ok | Dialog.Cancel; modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text { text: qsTr("Nombre de la playlist:"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: saveName; width: 280; text: root._mixTitle
                placeholderText: qsTr("Nombre de la playlist")
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
