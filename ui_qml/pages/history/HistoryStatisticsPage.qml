import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Drawer {
    id: root

    property var bridge: null
    property var _stats: null
    property string _listeningTimeToday: ""
    property string _listeningTimeWeek: ""
    property string _listeningTimeMonth: ""
    property string _listeningTimeAll: ""
    property string _state: "LOADING"

    signal closeRequested()
    signal exportRequested()
    signal playTrackRequested(string trackId)
    signal navigateToTrackRequested(string trackId)

    // title: qsTr("Estadísticas") (Drawer doesn't have title)
    width: Math.min(parent ? parent.width * 0.85 : 480, 560)
    height: parent ? parent.height : 600
    edge: Qt.RightEdge
    modal: true
    closePolicy: Popup.CloseOnEscape
    objectName: "historyStatisticsPage"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Estadísticas del historial"

    function refresh() {
        root._state = "LOADING"
        if (!root.bridge || typeof root.bridge.getStatistics === "undefined") {
            root._state = "ERROR"
            return
        }
        root._stats = root.bridge.getStatistics()
        if (!root._stats || !root._stats.ok) {
            root._state = "ERROR"
            return
        }
        _formatListeningTimes()
        root._state = "READY"
    }

    function _formatListeningTimes() {
        if (!root._stats) return
        var secs = root._stats.listening_time_today || 0
        root._listeningTimeToday = _fmtDuration(secs)
        secs = root._stats.listening_time_week || 0
        root._listeningTimeWeek = _fmtDuration(secs)
        secs = root._stats.listening_time_month || 0
        root._listeningTimeMonth = _fmtDuration(secs)
        secs = root._stats.listening_time_all || 0
        root._listeningTimeAll = _fmtDuration(secs)
    }

    function _fmtDuration(secs) {
        if (!secs || secs <= 0) return "0 min"
        var h = Math.floor(secs / 3600)
        var m = Math.floor((secs % 3600) / 60)
        if (h > 0) return h + "h " + m + "m"
        return m + " min"
    }

    onOpened: root.refresh()
    onClosed: root.closeRequested()

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.md

                Text {
                    text: qsTr("Estadísticas")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }
    focus: true

                MichiButton {
                    Accessible.role: Accessible.Button

                    id: exportStatsBtn
                    text: qsTr("Exportar")
                    variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.tab: closeStatsBtn
                    KeyNavigation.backtab: listeningTimeTodayCard
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.exportRequested()
                }

                    Accessible.role: Accessible.Button

                MichiButton {
                    id: closeStatsBtn
                    text: qsTr("Cerrar")
                    variant: "ghost"
                    activeFocusOnTab: true
                    KeyNavigation.backtab: exportStatsBtn
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.close()
                }
            }

            LoadingState {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                visible: root._state === "LOADING"
                title: qsTr("Cargando estadísticas")
                message: qsTr("Obteniendo datos del historial...")
            }

            ErrorState {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                visible: root._state === "ERROR"
                title: qsTr("Error al cargar estadísticas")
                message: !root.bridge ? "El servicio de estadísticas no está disponible."
                                      : "No se pudieron cargar los datos."
                showRetry: true
                onRetryRequested: root.refresh()
            }

            Item {
                width: parent.width
                height: 1
                visible: root._state !== "READY"
            }

            SectionHeader {
                text: qsTr("Tiempo de escucha")
                width: parent.width
                visible: root._state === "READY"
            }

            Row {
                spacing: MichiTheme.spacing.md
                width: parent.width
                visible: root._state === "READY"

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md * 3) / 4
                    height: 80
                    title: root._listeningTimeToday
                    subtitle: qsTr("Hoy")
                    KeyNavigation.tab: listeningTimeWeekCard
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                }
                GlassCard {
                    id: listeningTimeWeekCard
                    width: (parent.width - MichiTheme.spacing.md * 3) / 4
                    height: 80
                    title: root._listeningTimeWeek
                    subtitle: qsTr("Esta semana")
                    KeyNavigation.tab: listeningTimeMonthCard
                    KeyNavigation.backtab: listeningTimeTodayCard
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                }
                GlassCard {
                    id: listeningTimeMonthCard
                    width: (parent.width - MichiTheme.spacing.md * 3) / 4
                    height: 80
                    title: root._listeningTimeMonth
                    subtitle: qsTr("Este mes")
                    KeyNavigation.tab: listeningTimeAllCard
                    KeyNavigation.backtab: listeningTimeWeekCard
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                }
                GlassCard {
                    id: listeningTimeAllCard
                    width: (parent.width - MichiTheme.spacing.md * 3) / 4
                    height: 80
                    title: root._listeningTimeAll
                    subtitle: qsTr("Total")
                    KeyNavigation.backtab: listeningTimeMonthCard
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                }
            }

            SectionHeader {
                text: qsTr("Más reproducidas")
                width: parent.width
                showChevron: true
                visible: root._state === "READY"

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("history")
                    }
                }
            }

            Repeater {
                model: root._stats && root._stats.top_tracks ? root._stats.top_tracks.slice(0, 10) : []
                visible: root._state === "READY"

                Rectangle {
                    width: parent.width
                    height: 36
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: 24
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.35
                            text: modelData.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30
                            text: modelData.artist || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.15
                            text: modelData.play_count ? modelData.play_count + " plays" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true


                        MichiButton {
                            width: MichiTheme.minimumInteractiveSize
                            height: MichiTheme.minimumInteractiveSize
                            text: qsTr("▶")
                            variant: "ghost"
                            anchors.verticalCenter: parent.verticalCenter
                            visible: mouseArea.containsMouse
                            Accessible.name: "Reproducir elemento del historial"
                            onClicked: {
                                if (modelData.track_id)
                                    root.playTrackRequested(modelData.track_id)
                                else if (root.bridge && typeof root.bridge.playHistoryItem !== "undefined")
                                    root.bridge.playHistoryItem(String(modelData.track_id || modelData.id || ""))
                            }
                        }
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.track_id)
                                root.navigateToTrackRequested(modelData.track_id)
                            else if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigateWithParams("track_detail", {
                                    trackId: modelData.track_id || modelData.id || ""
                                })
                        }
                    }

                    Keys.onReturnPressed: mouseArea.clicked(mouseArea)
                    Keys.onSpacePressed: mouseArea.clicked(mouseArea)
                }
            }

            SectionHeader {
                text: qsTr("Álbumes más reproducidos")
                width: parent.width
                showChevron: true
                visible: root._state === "READY"

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("history")
                    }
                }
            }

            Repeater {
                model: root._stats && root._stats.top_albums ? root._stats.top_albums.slice(0, 10) : []
                visible: root._state === "READY"

                Rectangle {
                    width: parent.width
                    height: 36
                    color: mouseArea2.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: 24
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.40
                            text: modelData.album || modelData.name || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30
                            text: modelData.artist || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.play_count ? modelData.play_count + " plays" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: mouseArea2
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }
            }

            SectionHeader {
                text: qsTr("Artistas más reproducidos")
                width: parent.width
                showChevron: true
                visible: root._state === "READY"

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("history")
                    }
                }
            }

            Repeater {
                model: root._stats && root._stats.top_artists ? root._stats.top_artists.slice(0, 10) : []
                visible: root._state === "READY"

                Rectangle {
                    width: parent.width
                    height: 36
                    color: mouseArea3.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: 24
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.50
                            text: modelData.artist || modelData.name || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.play_count ? modelData.play_count + " plays" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: mouseArea3
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }
            }

            SectionHeader {
                text: qsTr("Distribución por género")
                width: parent.width
                showChevron: true
                visible: root._state === "READY"

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("history")
                    }
                }
            }

            Repeater {
                model: root._stats && root._stats.genre_breakdown ? root._stats.genre_breakdown : []
                visible: root._state === "READY"

                Rectangle {
                    width: parent.width
                    height: 36
                    color: mouseArea4.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radius.sm

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: parent.width * 0.50
                            text: modelData.genre || modelData.name || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Rectangle {
                            width: parent.width * 0.30
                            height: 8
                            radius: MichiTheme.radius.pill
                            color: MichiTheme.colors.controlTrack
                            anchors.verticalCenter: parent.verticalCenter

                            Rectangle {
                                width: parent.width * Math.min(1, (modelData.percentage || 0) / 100)
                                height: parent.height
                                radius: MichiTheme.radius.pill
                                color: MichiTheme.colors.accentBlue
                            }
                        }

                        Text {
                            text: modelData.play_count ? modelData.play_count + "" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: mouseArea4
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }
            }

            Item { width: 1; height: MichiTheme.spacing.lg }
        }
    }

    Keys.onEscapePressed: root.close()
}
