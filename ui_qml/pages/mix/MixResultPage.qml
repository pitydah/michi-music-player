import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mix Result"
    objectName: "mixResultPage"
    focus: true
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _songs: []
    property string _mixType: ""
    property bool _loading: false
    property string _errorMessage: ""

    signal backRequested()
    signal playAllRequested()
    signal enqueueAllRequested()
    signal saveAsPlaylistRequested()
    signal regenerateRequested()
    signal playTrackAtIndex(int index)

    objectName: "MixResultPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Resultados del Mix"

    ListView {
        id: trackList
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        clip: true; spacing: 2
        model: root._songs
        activeFocusOnTab: true
        objectName: "mixResultTrackList"
        Accessible.name: "Lista de canciones del mix"
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
                    text: "Volver"; variant: "ghost"
                    objectName: "resultBackBtn"
                    Accessible.name: "Volver al generador"
                    activeFocusOnTab: true
                    KeyNavigation.tab: playAllBtn
                    onClicked: root.backRequested()
                }

                Text {
                    text: "Mix — " + root._songs.length + " canciones"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    id: playAllBtn
                    text: "Reproducir todo"; variant: "primary"
                    objectName: "playAllBtn"
                    Accessible.name: "Reproducir todas las canciones del mix"
                    activeFocusOnTab: true
                    KeyNavigation.tab: enqueueAllBtn
                    KeyNavigation.backtab: resultBackBtn
                    enabled: root._songs.length > 0
                    onClicked: root.playAllRequested()
                }

                MichiButton {
                    id: enqueueAllBtn
                    text: "Agregar a cola"; variant: "secondary"
                    objectName: "enqueueAllBtn"
                    Accessible.name: "Agregar todas las canciones a la cola"
                    activeFocusOnTab: true
                    KeyNavigation.tab: saveAsPlaylistBtn
                    KeyNavigation.backtab: playAllBtn
                    enabled: root._songs.length > 0
                    onClicked: root.enqueueAllRequested()
                }

                MichiButton {
                    id: saveAsPlaylistBtn
                    text: "Guardar como playlist"; variant: "ghost"
                    objectName: "saveAsPlaylistBtn"
                    Accessible.name: "Guardar mix como playlist"
                    activeFocusOnTab: true
                    KeyNavigation.tab: regenerateBtn
                    KeyNavigation.backtab: enqueueAllBtn
                    enabled: root._songs.length > 0
                    onClicked: root.saveAsPlaylistRequested()
                }

                MichiButton {
                    id: regenerateBtn
                    text: "Regenerar"; variant: "ghost"
                    objectName: "regenerateBtn"
                    Accessible.name: "Regenerar mix"
                    activeFocusOnTab: true
                    KeyNavigation.tab: trackList
                    KeyNavigation.backtab: saveAsPlaylistBtn
                    enabled: !root._loading
                    onClicked: root.regenerateRequested()
                }
            }

            Rectangle {
                width: parent.width; height: 1
                color: MichiTheme.colors.borderSubtle
            }
        }

        delegate: Rectangle {
            width: trackList.width; height: 48
            color: modelData._hovered ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm
            activeFocusOnTab: true
            objectName: "mixTrackItem_" + index
            Accessible.name: modelData.title + " - " + modelData.artist + (modelData.album ? " - " + modelData.album : "")
            KeyNavigation.tab: index < root._songs.length - 1
                ? trackList.itemAtIndex(index + 1)
                : null
            KeyNavigation.backtab: index > 0
                ? trackList.itemAtIndex(index - 1)
                : regenerateBtn

            Keys.onReturnPressed: onPlay()
            Keys.onSpacePressed: onPlay()

            property bool _hovered: false

            signal onPlay()

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

                Text {
                    width: 24; text: "P"; color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: root.playTrackAtIndex(index)
                    }
                }

                Text {
                    width: 24; text: "+"; color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.cardTitleSize; anchors.verticalCenter: parent.verticalCenter
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
                anchors.fill: parent; hoverEnabled: true
                onEntered: modelData._hovered = true
                onExited: modelData._hovered = false
                onClicked: {
                    if (modelData._onClick) modelData._onClick()
                }
            }
        }

        Text {
            anchors.centerIn: parent; visible: root._songs.length === 0
            text: "No hay canciones en este mix"
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
        }
    }

    LoadingState {
        anchors.centerIn: parent
        visible: root._loading
        title: "Cargando mix..."
    }

    ErrorState {
        anchors.centerIn: parent
        visible: root._errorMessage !== ""
        title: "Error"
        message: root._errorMessage
        showRetry: true
        onRetryRequested: root.regenerateRequested()
    }

    StatusBadge {
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
        anchors.margins: MichiTheme.spacing.md
        visible: root.mx === null
        text: "Bridge no disponible"
        kind: "disconnected"
    }
}
