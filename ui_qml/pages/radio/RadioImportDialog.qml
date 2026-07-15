import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var _importedStations: []
    property var _selectedIndices: []
    property bool _importing: false
    property int _importProgress: 0
    property int _importTotal: 0

    title: "Importar emisoras"
    modal: true
    width: Math.min(parent.width * 0.8, 500)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    padding: MichiTheme.spacing.lg

    objectName: "radioImportDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Importar emisoras"
    Accessible.description: "Importar emisoras desde archivo M3U, PLS o XSPF"

    function parseM3u(content) {
        var stations = []
        var lines = content.split("\n")
        var currentName = ""
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim()
            if (line === "") continue
            var extinfMatch = line.match(/^#EXTINF:-1,(.+)$/)
            if (extinfMatch) {
                currentName = extinfMatch[1].trim()
            } else if (!line.startsWith("#") && line.match(/^https?:\/\//)) {
                stations.push({
                    name: currentName || "Imported",
                    url: line,
                    selected: true
                })
                currentName = ""
            }
        }
        return stations
    }

    function parsePls(content) {
        var stations = []
        var lines = content.split("\n")
        var currentEntry = -1
        var nameMap = {}
        var fileMap = {}
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim()
            if (line.startsWith("File")) {
                var match = line.match(/^File(\d+)=(.+)$/)
                if (match) {
                    currentEntry = parseInt(match[1])
                    fileMap[currentEntry] = match[2].trim()
                }
            } else if (line.startsWith("Title")) {
                var match2 = line.match(/^Title(\d+)=(.+)$/)
                if (match2) {
                    nameMap[parseInt(match2[1])] = match2[2].trim()
                }
            }
        }
        for (var key in fileMap) {
            stations.push({
                name: nameMap[key] || "Imported",
                url: fileMap[key],
                selected: true
            })
        }
        return stations
    }

    function parseXspf(content) {
        var stations = []
        var trackRegex = /<track>([\s\S]*?)<\/track>/g
        var match
        while ((match = trackRegex.exec(content)) !== null) {
            var trackContent = match[1]
            var titleMatch = trackContent.match(/<title>([^<]*)<\/title>/)
            var locMatch = trackContent.match(/<location>([^<]*)<\/location>/)
            stations.push({
                name: titleMatch ? titleMatch[1].trim() : "Imported",
                url: locMatch ? locMatch[1].trim() : "",
                selected: true
            })
        }
        return stations.filter(function(s) { return s.url !== "" })
    }

    function loadFile(fileUrl) {
        var path = fileUrl.toString().replace("file://", "")
        if (path === "") return

        var xhr = new XMLHttpRequest()
        xhr.open("GET", fileUrl.toString())
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 0 || xhr.status === 200) {
                    var content = xhr.responseText
                    var stations = []
                    if (path.match(/\.pls$/i)) {
                        stations = parsePls(content)
                    } else if (path.match(/\.xspf$/i)) {
                        stations = parseXspf(content)
                    } else {
                        stations = parseM3u(content)
                    }
                    root._importedStations = stations
                    root._selectedIndices = []
                    for (var si = 0; si < stations.length; si++) {
                        root._selectedIndices.push(si)
                    }
                }
            }
        }
        xhr.send()
    }

    function toggleStation(index) {
        var idx = root._selectedIndices.indexOf(index)
        if (idx >= 0) {
            root._selectedIndices.splice(idx, 1)
        } else {
            root._selectedIndices.push(index)
        }
        root._selectedIndices = root._selectedIndices.slice()
    }

    function selectAll() {
        root._selectedIndices = []
        for (var i = 0; i < root._importedStations.length; i++) {
            root._selectedIndices.push(i)
        }
        root._selectedIndices = root._selectedIndices.slice()
    }

    function deselectAll() {
        root._selectedIndices = []
        root._selectedIndices = root._selectedIndices.slice()
    }

    function doImport() {
        if (root._importing) return
        root._importing = true
        root._importProgress = 0
        root._importTotal = root._selectedIndices.length

        for (var i = 0; i < root._selectedIndices.length; i++) {
            var station = root._importedStations[root._selectedIndices[i]]
            if (station && root.rd && typeof root.rd.addStation === "function") {
                root.rd.addStation(station.name, station.url, "", "")
            }
            root._importProgress = i + 1
        }

        root._importing = false
        if (root.notif) {
            root.notif.showMessage("Importadas " + root._importProgress + " emisoras", "success")
        }
        root.close()
    }

    FileDialog {
        id: fileDialog
        title: "Seleccionar archivo de emisoras"
        nameFilters: [
            "Formatos de emisoras (*.m3u *.pls *.xspf)",
            "M3U (*.m3u)", "PLS (*.pls)", "XSPF (*.xspf)",
            "Todos (*)"
        ]
        onAccepted: root.loadFile(selectedFile)
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            MichiButton {
                text: "Seleccionar archivo..."
                variant: "primary"
                onClicked: fileDialog.open()
                objectName: "radioImportDialog.fileButton"
                Accessible.name: "Seleccionar archivo para importar"
            }

            MichiButton {
                text: "Seleccionar todos"
                variant: "ghost"
                visible: root._importedStations.length > 0
                onClicked: selectAll()
                objectName: "radioImportDialog.selectAllButton"
                Accessible.name: "Seleccionar todas las emisoras"
            }

            MichiButton {
                text: "Deseleccionar todos"
                variant: "ghost"
                visible: root._importedStations.length > 0
                onClicked: deselectAll()
                objectName: "radioImportDialog.deselectAllButton"
                Accessible.name: "Deseleccionar todas las emisoras"
            }
        }

        Text {
            text: root._importedStations.length > 0
                ? root._importedStations.length + " emisoras encontradas. " + root._selectedIndices.length + " seleccionadas."
                : "Selecciona un archivo M3U, PLS o XSPF para importar emisoras."
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            width: parent.width
            wrapMode: Text.WordWrap
        }

        Flickable {
            width: parent.width
            height: Math.min(root._importedStations.length * 40, 300)
            clip: true
            visible: root._importedStations.length > 0
            contentHeight: previewColumn.height

            Column {
                id: previewColumn
                width: parent.width
                spacing: 2

                Repeater {
                    model: root._importedStations

                    Rectangle {
                        width: parent.width
                        height: 38
                        color: root._selectedIndices.indexOf(index) >= 0
                            ? MichiTheme.colors.accentSurface : "transparent"
                        radius: MichiTheme.radiusSm

                        Row {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.sm

                            CheckBox {
                                id: stationCheck
                                checked: root._selectedIndices.indexOf(index) >= 0
                                onCheckedChanged: root.toggleStation(index)
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Column {
                                width: parent.width - 50
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 1

                                Text {
                                    text: modelData.name || ""
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: modelData.url || ""
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    elide: Text.ElideMiddle
                                    width: parent.width
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleStation(index)
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 6
            radius: 3
            color: MichiTheme.colors.controlTrack
            visible: root._importing

            Rectangle {
                width: parent.width * (root._importProgress / Math.max(root._importTotal, 1))
                height: parent.height
                radius: 3
                color: MichiTheme.colors.accent

                Behavior on width {
                    NumberAnimation { duration: MichiTheme.motion.fast }
                }
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                enabled: !root._importing
                onClicked: {
                    root._importedStations = []
                    root._selectedIndices = []
                    root.close()
                }
                objectName: "radioImportDialog.cancelButton"
                Accessible.name: "Cancelar importación"
            }

            MichiButton {
                text: "Importar " + root._selectedIndices.length + " emisoras"
                variant: "primary"
                enabled: root._selectedIndices.length > 0 && !root._importing
                onClicked: doImport()
                objectName: "radioImportDialog.importButton"
                Accessible.name: "Importar emisoras seleccionadas"
            }
        }
    }
}
