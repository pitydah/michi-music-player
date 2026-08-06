import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Mix Result")
    objectName: "mixResultPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _songs: []
    property string _mixType: ""
    property bool _loading: false
    property bool _waiting: false
    property string _errorMessage: ""

    signal backRequested()

    Connections {
        target: root.mx
        function onStateChanged(state) {
            if (!root._waiting) return
            if (state === "COMPLETED_WITH_TRACKS" || state === "PARTIAL_RECOMMENDATION") {
                root._waiting = false
                root._loading = false
                root.refresh()
            } else if (state === "CANCELLED") {
                root._waiting = false
                root._loading = false
            } else {
                root._waiting = false
                root._loading = false
                root._errorMessage = root.mx.errorMessage || qsTr("Error al regenerar el mix")
            }
        }
    }

    function routeEnter(route, params) {
        root.refresh()
    }

    function refresh() {
        if (!root.mx) {
            root._songs = []
            return
        }
        root._songs = root.mx.currentSongs || []
        root._errorMessage = root.mx.errorMessage || ""
    }

    function playAll() {
        if (root.mx && typeof root.mx.playMix === "function")
            root.mx.playMix()
    }

    function enqueueAll() {
        if (root.mx && typeof root.mx.enqueueMix === "function")
            root.mx.enqueueMix()
    }

    function regenerate() {
        if (!root.mx || typeof root.mx.regenerate !== "function")
            return
        root._loading = true
        root._errorMessage = ""
        root._waiting = false
        var result = root.mx.regenerate()
        if (result && result.ok) {
            if (root.mx.currentSongs && root.mx.currentSongs.length > 0) {
                root._loading = false
                root.refresh()
            } else {
                root._waiting = true
            }
        } else {
            root._loading = false
            root._errorMessage = (result && result.error) || qsTr("Error al regenerar el mix")
        }
    }

    function playTrack(index) {
        if (root.mx && typeof root.mx.playFromIndex === "function")
            root.mx.playFromIndex(index)
    }

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: qsTr("Canciones del mix")

        focusPolicy: Qt.StrongFocus
        id: trackList
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        clip: true; spacing: 2
        model: root._songs
        activeFocusOnTab: true
        headerPositioning: ListView.OverlayHeader
        focus: true

        header: Column {
            width: trackList.width; spacing: MichiTheme.spacing.md
            z: 2

            Rectangle {
                width: parent.width; height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    text: qsTr("Volver"); variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: playAllBtn
                    onClicked: {
                        root.backRequested()
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }
                }

                Text {
                    text: qsTr("Mix — %1 canciones").arg(root._songs.length); color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    id: playAllBtn
                    text: qsTr("Reproducir todo"); variant: "primary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: enqueueAllBtn
                    enabled: root._songs.length > 0
                    onClicked: root.playAll()
                }

                MichiButton {
                    id: enqueueAllBtn
                    text: qsTr("Agregar a cola"); variant: "secondary"
                    activeFocusOnTab: true
                    KeyNavigation.tab: saveAsPlaylistBtn
                    KeyNavigation.backtab: playAllBtn
                    enabled: root._songs.length > 0
                    onClicked: root.enqueueAll()
                }

                MichiButton {
                    id: saveAsPlaylistBtn
                    text: qsTr("Guardar como playlist"); variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: regenerateBtn
                    KeyNavigation.backtab: enqueueAllBtn
                    enabled: root._songs.length > 0
                    onClicked: saveDialog.open()
                }

                MichiButton {
                    id: regenerateBtn
                    text: qsTr("Regenerar"); variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: trackList
                    KeyNavigation.backtab: saveAsPlaylistBtn
                    enabled: !root._loading
                    onClicked: root.regenerate()
                }
            }

            Rectangle {
                width: parent.width; height: 1
                color: MichiTheme.colors.borderSubtle
            }
        }

        delegate: Rectangle {
            width: trackList.width; height: 48
            color: rowHover.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radius.sm
            activeFocusOnTab: true
            KeyNavigation.tab: index < root._songs.length - 1
                ? trackList.itemAtIndex(index + 1)
                : null
            KeyNavigation.backtab: index > 0
                ? trackList.itemAtIndex(index - 1)
                : regenerateBtn

            Keys.onReturnPressed: root.playTrack(index)
            Keys.onSpacePressed: root.playTrack(index)

            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                Text {
                    width: 24; text: index + 1; color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                }

                Text {
                    width: parent.width * 0.30; text: modelData.title || ""
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    width: parent.width * 0.20; text: modelData.artist || ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    width: parent.width * 0.20; text: modelData.album || ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
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
                        onClicked: root.playTrack(index)
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
                            if (root.mx && typeof root.mx.enqueueTrack === "function")
                                root.mx.enqueueTrack(index)
                        }
                    }
                }
            }

            MouseArea {
                id: rowHover
                anchors.fill: parent; hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }

        Text {
            anchors.centerIn: parent; visible: root._songs.length === 0
            text: qsTr("No hay canciones en este mix")
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
        }
    }

    MichiLoadingState {
        anchors.centerIn: parent
        visible: root._loading
        title: qsTr("Cargando mix...")
    }

    ErrorState {
        anchors.centerIn: parent
        visible: root._errorMessage !== ""
        title: qsTr("Error")
        message: root._errorMessage
        showRetry: true
        onRetryRequested: root.regenerate()
    }

    StatusBadge {
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
        anchors.margins: MichiTheme.spacing.md
        visible: root.mx === null
        text: qsTr("Bridge no disponible")
        kind: "disconnected"
    }

    Dialog {
        id: saveDialog
        title: qsTr("Guardar mix como playlist")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3

        Column {
            spacing: MichiTheme.spacing.md
            Text {
                text: qsTr("Nombre de la playlist:")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: saveName; width: 280
                placeholderText: qsTr("Nombre de la playlist")
            }
        }

        onAccepted: {
            var name = saveName.text.trim()
            if (name && root.mx && typeof root.mx.saveMixAsPlaylist === "function")
                root.mx.saveMixAsPlaylist(name)
        }
    }

    Component.onCompleted: root.refresh()
}
