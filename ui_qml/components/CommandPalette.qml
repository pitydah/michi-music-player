import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property var cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
    property var cap: typeof capabilityBridge !== "undefined" ? capabilityBridge : null
    property bool open: false
    property var _results: []
    property var _recentActions: []
    property int _maxRecent: 5
    property var _sections: ["Routes", "Actions", "Playback", "Tracks", "Albums", "Artists", "Playlists", "Settings", "Devices", "Audio Lab"]
    property string _query: ""
    property int _selIndex: -1
    property bool _debouncePending: false

    objectName: "commandPalette"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Paleta de comandos"
    Accessible.description: "Busca y ejecuta comandos rápidamente"

    visible: open

    function openPalette() {
        root.open = true
        root._selIndex = -1
        root._query = ""
        searchField.text = ""
        root._debouncePending = false
        searchField.forceActiveFocus()
    }

    function closePalette() {
        root.open = false
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9998

        MouseArea {
            anchors.fill: parent
            onClicked: root.closePalette()
            Accessible.name: "Cerrar paleta de comandos"
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 480; height: 400
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfaceCardElevated
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        z: 9999

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            TextField {
                id: searchField
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                placeholderText: "Buscar comando (Ctrl+P)..."
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                placeholderTextColor: MichiTheme.colors.textMuted
                background: Rectangle {
                    radius: MichiTheme.radiusSm
                    color: MichiTheme.colors.surfaceInput
                    border.width: searchField.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                    border.color: searchField.activeFocus ? MichiTheme.colors.borderActive : MichiTheme.colors.borderInner
                }
                leftPadding: MichiTheme.spacing.md
                rightPadding: MichiTheme.spacing.md
                objectName: "commandPalette.searchField"
                Accessible.name: "Campo de búsqueda de comandos"
                Accessible.description: "Escribe para buscar comandos"

                Keys.onEscapePressed: root.closePalette()
                Keys.onReturnPressed: executeSelected()
                Keys.onUpPressed: {
                    if (root._selIndex > 0) root._selIndex--
                    else root._selIndex = root._results.length - 1
                    listView.positionViewAtIndex(root._selIndex, ListView.Contain)
                }
                Keys.onDownPressed: {
                    if (root._selIndex < root._results.length - 1) root._selIndex++
                    else root._selIndex = 0
                    listView.positionViewAtIndex(root._selIndex, ListView.Contain)
                }

                onTextChanged: {
                    root._query = text
                    root._debouncePending = true
                    debounceTimer.restart()
                }
            }

            Timer {
                id: debounceTimer
                interval: 150
                onTriggered: {
                    root._debouncePending = false
                    root.doSearch(root._query)
                }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 20
                color: "transparent"
                visible: root._recentActions.length > 0 && root._query === ""

                RowLayout {
                    anchors.fill: parent
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Recientes"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Repeater {
                        model: root._recentActions

                        Rectangle {
                            height: 18
                            width: label.implicitWidth + 12
                            radius: MichiTheme.radiusXs
                            color: MichiTheme.colors.accentSurface

                            Text {
                                id: label
                                anchors.centerIn: parent
                                text: modelData.title || ""
                                color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.badgeSize
                                font.weight: MichiTheme.typography.weightMedium
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root._execute(modelData.id || "")
                                Accessible.name: "Acción reciente: " + (modelData.title || "")
                            }
                        }
                    }
                }
            }

            ListView {
                id: listView
                Layout.fillWidth: true; Layout.fillHeight: true
                model: root._results
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                objectName: "commandPalette.results"
                Accessible.name: "Resultados de búsqueda de comandos"

                ScrollBar.vertical: ScrollBar {
                    width: 6; policy: ScrollBar.AsNeeded
                }

                section.property: "category"
                section.criteria: ViewSection.FullString
                section.delegate: Rectangle {
                    width: parent.width; height: 24
                    color: "transparent"
                    Text {
                        anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: {
                            var sectionKey = section
                            if (sectionKey === "navigation") return "Navegación"
                            if (sectionKey === "playback") return "Reproducción"
                            if (sectionKey === "library") return "Biblioteca"
                            if (sectionKey === "playlist") return "Listas"
                            if (sectionKey === "metadata") return "Metadatos"
                            if (sectionKey === "system") return "Sistema"
                            if (sectionKey === "track") return "Canciones"
                            if (sectionKey === "album") return "Álbumes"
                            if (sectionKey === "artist") return "Artistas"
                            if (sectionKey === "folder") return "Carpetas"
                            if (sectionKey === "source") return "Fuentes"
                            if (sectionKey === "radio") return "Radio"
                            return sectionKey.charAt(0).toUpperCase() + sectionKey.slice(1)
                        }
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }
                }

                delegate: Rectangle {
                    id: delegate
                    width: parent.width; height: 36
                    color: index === root._selIndex ? MichiTheme.colors.accentSelection :
                           mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radiusXs

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Rectangle {
                            width: 24; height: 24; radius: MichiTheme.radiusXs
                            color: MichiTheme.colors.accentSurface
                            visible: modelData.icon !== undefined && modelData.icon !== ""

                            Text {
                                anchors.centerIn: parent
                                text: {
                                    var ic = modelData.icon || ""
                                    if (ic === "home") return "H"
                                    if (ic === "library" || ic === "folder") return "F"
                                    if (ic === "play" || ic === "playback") return "\u25B6"
                                    if (ic === "next") return "\u23ED"
                                    if (ic === "prev") return "\u23EE"
                                    if (ic === "queue") return "Q"
                                    if (ic === "playlist") return "P"
                                    if (ic === "radio") return "R"
                                    return ic.charAt(0).toUpperCase()
                                }
                                color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.metaSize
                                font.weight: MichiTheme.typography.weightBold
                            }
                        }

                        Column {
                            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
                            spacing: 1

                            Text {
                                text: modelData.title || ""
                                color: modelData.enabled !== false ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; width: parent.width
                            }

                            Text {
                                text: modelData.enabled === false ? "Acción no disponible en el estado actual" : ""
                                color: MichiTheme.colors.warning
                                font.pixelSize: MichiTheme.typography.metaSize
                                visible: text !== ""
                                Accessible.description: "Acción no disponible en el estado actual"
                            }
                        }

                        Text {
                            text: modelData.shortcut || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium
                            visible: modelData.shortcut !== undefined && modelData.shortcut !== ""
                            Accessible.name: "Atajo: " + (modelData.shortcut || "")
                        }

                        Text {
                            text: modelData.destructive ? "!" : ""
                            color: MichiTheme.colors.error
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightBold
                            visible: modelData.destructive === true
                        }
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root._selIndex = index
                            root._execute(modelData.id || "")
                        }
                        Accessible.name: "Ejecutar comando: " + (modelData.title || "")
                        Accessible.description: modelData.destructive ? "Acción destructiva" : ""
                    }
                }

                Item {
                    width: parent.width; height: 80
                    visible: root._results.length === 0 && root._query !== ""

                    Column {
                        anchors.centerIn: parent; spacing: MichiTheme.spacing.sm
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Sin resultados"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "No se encontraron comandos para \"" + root._query + "\""
                            color: MichiTheme.colors.textMeta
                            font.pixelSize: MichiTheme.typography.metaSize
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 22
                color: MichiTheme.colors.borderInner
                radius: MichiTheme.radiusSm

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.sm; anchors.rightMargin: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root._results.length > 0 ? root._results.length + " comandos" : ""
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: 9
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "\u2191\u2193 Navegar"
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: 9
                    }
                    Text {
                        text: "Enter Ejecutar"
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: 9
                    }
                    Text {
                        text: "Esc Cerrar"
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: 9
                    }
                }
            }
        }
    }

    Shortcut {
        sequence: "Escape"
        onActivated: { if (root.open) root.closePalette() }
    }

    function doSearch(query) {
        var q = query.toLowerCase().trim()
        if (root.cpb && root.cpb.searchCommands) {
            root._results = root.cpb.searchCommands(q)
        } else {
            root._results = []
        }
        root._selIndex = -1

        if (q !== "" && root.cap && root.cap.capabilities) {
            var caps = root.cap.capabilities
            root._results = root._results.filter(function(a) {
                if (a.id.indexOf("radio") >= 0 && caps.has_radio === false) return false
                if (a.id.indexOf("sync") >= 0 && caps.has_sync === false) return false
                if (a.id.indexOf("home_audio") >= 0 && caps.has_home_audio === false) return false
                return true
            })
        }

        if (q === "" && root._results.length === 0 && root.cpb && root.cpb.commands) {
            root._results = root.cpb.commands
        }
    }

    function executeSelected() {
        if (root._selIndex >= 0 && root._selIndex < root._results.length) {
            root._execute(root._results[root._selIndex].id || "")
        } else if (root._results.length > 0) {
            root._selIndex = 0
            root._execute(root._results[0].id || "")
        }
    }

    function _execute(id) {
        if (!id) return
        var action = null
        for (var i = 0; i < root._results.length; i++) {
            if (root._results[i].id === id) {
                action = root._results[i]
                break
            }
        }
        if (!action) {
            if (root.cpb && root.cpb.commands) {
                var allCmds = root.cpb.commands
                for (var j = 0; j < allCmds.length; j++) {
                    if (allCmds[j].id === id) {
                        action = allCmds[j]
                        break
                    }
                }
            }
        }
        if (!action) return
        if (action.enabled === false) return

        var recent = root._recentActions
        recent = recent.filter(function(a) { return a.id !== id })
        recent.unshift({id: id, title: action.title || ""})
        if (recent.length > root._maxRecent) recent = recent.slice(0, root._maxRecent)
        root._recentActions = recent

        if (root.cpb && root.cpb.executeCommand) {
            root.cpb.executeCommand(id)
        }
        root.closePalette()
    }
}
