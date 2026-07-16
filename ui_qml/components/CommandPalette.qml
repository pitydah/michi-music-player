import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    objectName: "commandPalette"
    focus: true
    id: root

    property var cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
    property var capb: typeof capabilityBridge !== "undefined" ? capabilityBridge : null
    property alias shortcut: paletteShortcut
    property bool open: false
    property var _results: []
    property var _recentActions: []
    property int _selectedIndex: -1
    property string _filterText: ""

    visible: open

    Accessible.role: Accessible.Dialog
    Accessible.name: "Paleta de comandos"

    Shortcut {
        id: paletteShortcut
        sequences: ["Ctrl+P", "Ctrl+P"]
        enabled: true
        onActivated: {
            root.open = !root.open
            if (root.open) {
                searchField.forceActiveFocus()
                searchField.selectAll()
            }
        }
    }

    Keys.onEscapePressed: closePalette()
    Keys.onUpPressed: navigateUp()
    Keys.onDownPressed: navigateDown()
    Keys.onReturnPressed: activateSelected()
    Keys.onTabPressed: cycleSection()

    function closePalette() {
        root.open = false
        root._selectedIndex = -1
        root._filterText = ""
    }

    function navigateUp() {
        if (root._selectedIndex > 0) {
            root._selectedIndex--
            listView.positionViewAtIndex(root._selectedIndex, ListView.Contain)
        }
    }

    function navigateDown() {
        if (root._selectedIndex < root._results.length - 1) {
            root._selectedIndex++
            listView.positionViewAtIndex(root._selectedIndex, ListView.Contain)
        }
    }

    function activateSelected() {
        if (root._selectedIndex >= 0 && root._selectedIndex < root._results.length) {
            var item = root._results[root._selectedIndex]
            executeItem(item)
        }
    }

    function cycleSection() {
        if (root._results.length === 0) return
        var currentSection = root._selectedIndex >= 0 ? root._results[root._selectedIndex].category : ""
        var start = (root._selectedIndex + 1) % root._results.length
        var i = start
        while (true) {
            if (root._results[i].category !== currentSection) {
                root._selectedIndex = i
                listView.positionViewAtIndex(root._selectedIndex, ListView.Contain)
                return
            }
            i = (i + 1) % root._results.length
            if (i === start) break
        }
    }

    function executeItem(item) {
        if (!item || !item.id) return
        if (item._unavailable) return

        if (root.cpb && typeof root.cpb.executeCommand !== "undefined") {
            root.cpb.executeCommand(item.id)
        }

        addToRecent(item)
        closePalette()
    }

    function addToRecent(item) {
        for (var i = 0; i < root._recentActions.length; i++) {
            if (root._recentActions[i].id === item.id) {
                root._recentActions.splice(i, 1)
                break
            }
        }
        root._recentActions.unshift(item)
        if (root._recentActions.length > 10) {
            root._recentActions.pop()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9998

        MouseArea {
            anchors.fill: parent
            onClicked: root.closePalette()
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 480
        height: Math.min(420, parent.height * 0.7)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
        z: 9999

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: parent.width
                height: 40
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surfaceInput
                border.color: searchField.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                border.width: searchField.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth

                TextInput {
                    Accessible.role: Accessible.EditableText

                    Accessible.name: "Campo de texto"

                    id: searchField
                    anchors.fill: parent
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.rightMargin: MichiTheme.spacing.md
                    anchors.topMargin: MichiTheme.spacing.xs
                    anchors.bottomMargin: MichiTheme.spacing.xs
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    verticalAlignment: TextInput.AlignVCenter
                    activeFocusOnTab: true

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Buscar comando…"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: parent.text === "" && !parent.activeFocus
                    }

                    onTextChanged: {
                        root._filterText = text
                        debounceSearch.restart()
                    }

                    Keys.onEscapePressed: root.closePalette()
                    Keys.onUpPressed: root.navigateUp()
                    Keys.onDownPressed: root.navigateDown()
                    Keys.onReturnPressed: root.activateSelected()
                    Keys.onTabPressed: root.cycleSection()
                }
            }

            Timer {
                id: debounceSearch
                interval: 150
                repeat: false
                onTriggered: searchCommands(root._filterText)
            }
                Accessible.role: Accessible.List

                Accessible.name: "ListView"


            ListView {
                focusPolicy: Qt.StrongFocus
                id: listView
                width: parent.width
                height: parent.height - searchField.height - MichiTheme.spacing.lg - sectionBar.height - MichiTheme.spacing.sm
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                activeFocusOnTab: true

                model: root._results
                currentIndex: root._selectedIndex

                delegate: Rectangle {
                    width: listView.width
                    height: 36
                    color: index === listView.currentIndex ? MichiTheme.colors.accentSelection : "transparent"
                    radius: MichiTheme.radiusXs
                    Accessible.description: modelData._unavailable ? "Acción no disponible en el estado actual" : ""

                    Rectangle {
                        visible: root._filterText === "" && root._recentActions.length > 0 && index < root._recentActions.length
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: MichiTheme.spacing.xs
                        width: 4
                        height: 4
                        radius: 2
                        color: MichiTheme.colors.experimental
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.title || ""
                        color: modelData._unavailable ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: modelData._unavailable ? MichiTheme.typography.weightNormal : MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width * 0.55
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.right: shortcutLabel.left
                        anchors.rightMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.category || ""
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: MichiTheme.typography.captionSize
                        visible: modelData._unavailable
                        elide: Text.ElideRight
                    }

                    Text {
                        id: shortcutLabel
                        anchors.right: parent.right
                        anchors.rightMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.shortcut || ""
                        color: MichiTheme.colors.textMeta
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: modelData.shortcut !== ""
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: "No disponible"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: modelData._unavailable
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: modelData._unavailable ? Qt.ArrowCursor : Qt.PointingHandCursor
                        onClicked: {
                            if (!modelData._unavailable) {
                                listView.currentIndex = index
                                root.executeItem(modelData)
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 6
                }
            }

            Rectangle {
                id: sectionBar
                width: parent.width
                height: 28
                color: "transparent"

                Row {
                    anchors.fill: parent
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: getVisibleSections()

                        Rectangle {
                            height: parent.height
                            width: sectionText.implicitWidth + MichiTheme.spacing.md
                            radius: MichiTheme.radiusPill
                            color: MichiTheme.colors.surfaceSubtle
                            border.color: MichiTheme.colors.borderInner
                            border.width: MichiTheme.borderWidth

                            Text {
                                id: sectionText
                                anchors.centerIn: parent
                                text: modelData
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }
                    }
                }
            }
        }
    }

    function getVisibleSections() {
        var sections = []
        var seen = {}
        for (var i = 0; i < root._results.length; i++) {
            var cat = root._results[i].category
            if (!seen[cat]) {
                seen[cat] = true
                sections.push(cat)
            }
        }
        return sections
    }

    function searchCommands(query) {
        var q = query.toLowerCase().trim()
        var all = root.cpb && typeof root.cpb.searchCommands !== "undefined" ? root.cpb.searchCommands(query) : []

        var caps = root.capb && typeof root.capb.capabilities !== "undefined" ? root.capb.capabilities : ({})

        var results = []
        for (var i = 0; i < all.length; i++) {
            var item = all[i]
            var copy = {}
            for (var key in item) {
                copy[key] = item[key]
            }
            if (!capabilityAllowed(copy, caps)) {
                copy._unavailable = true
            } else {
                copy._unavailable = false
            }
            results.push(copy)
        }

        root._results = results
        root._selectedIndex = results.length > 0 ? 0 : -1
    }

    function capabilityAllowed(action, caps) {
        if (!action || !action.id) return true
        var requirements = {
            "radio_add_station": "has_radio",
            "navigate_radio": "has_radio",
            "navigate_home_audio": "has_home_audio",
            "navigate_queue": "has_queue",
            "track_analyze_audio_lab": "has_audio_lab",
            "album_analyze": "has_audio_lab",
            "track_check_integrity": "has_audio_lab",
            "track_calculate_replaygain": "has_replaygain",
            "playback_volume_up": "has_volume",
            "playback_volume_down": "has_volume",
            "playback_mute": "has_volume",
            "playback_seek_forward": "has_seek",
            "playback_seek_back": "has_seek",
            "source_add": "has_subsonic",
            "source_edit": "has_subsonic",
            "source_remove": "has_subsonic",
            "source_scan": "has_subsonic",
            "source_cancel_scan": "has_subsonic",
            "metadata_smart_tagging": "has_smart_tagging",
            "track_send_to_device": "has_sync",
            "navigate_diagnostics": "has_diagnostics",
            "diagnostics_show": "has_diagnostics",
            "library_doctor": "has_library_doctor",
        }
        var required = requirements[action.id]
        if (required) {
            return caps[required] === true
        }
        return true
    }

    Connections {
        target: root.cpb
        function onCommandsChanged() {
            searchCommands(root._filterText)
        }
    }

    onOpenChanged: {
        if (root.open) {
            searchCommands("")
            searchField.forceActiveFocus()
        }
    }
}
