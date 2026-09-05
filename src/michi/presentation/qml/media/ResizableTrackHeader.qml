import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property real titleColumnWidth: LibraryTrackColumnState.titleWidth
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showArtwork: true
    property bool showActions: true
    property bool sortingEnabled: false
    property string sortColumn: ""
    property bool sortDescending: false
    signal sortRequested(string column)
    signal sortDirectionRequested(string column, bool descending)
    readonly property string titleResizeNeighbor:
        showArtistColumn && LibraryTrackColumnState.artistVisible ? "artist"
        : showAlbumColumn && LibraryTrackColumnState.albumVisible ? "album"
        : LibraryTrackColumnState.formatVisible ? "format"
        : LibraryTrackColumnState.durationVisible ? "duration" : ""

    implicitHeight: MichiMetrics.controlMedium
    color: MichiSemanticColors.controlSurface
    radius: MichiRadius.sm
    border.width: 1
    border.color: MichiSemanticColors.borderSubtle
    z: 2

    function resizeColumn(column, width) {
        LibraryTrackColumnState.setWidth(column, width)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        MichiText {
            Layout.preferredWidth: LibraryTrackColumnState.numberWidth
            text: qsTr("#")
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
            horizontalAlignment: Text.AlignHCenter
        }
        ResizableHeaderCell {
            visible: root.showArtwork && LibraryTrackColumnState.artworkVisible
            Layout.preferredWidth: LibraryTrackColumnState.artworkWidth
            label: qsTr("ART")
            columnKey: "artwork"
            columnWidth: LibraryTrackColumnState.artworkWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.titleVisible
            Layout.preferredWidth: root.titleColumnWidth
            label: qsTr("TITLE")
            columnKey: "title"
            columnWidth: root.titleColumnWidth
            resizeBaseWidth: LibraryTrackColumnState.titleWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => {
                if (root.titleResizeNeighbor.length > 0)
                    LibraryTrackColumnState.resizeWithNeighbor(
                        column, width, root.titleResizeNeighbor)
                else
                    root.resizeColumn(column, width)
            }
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            // LIB-A P2-A: right-click de Title abre el contexto EXACTO de
            // la columna (targetColumn = "title" — nunca el global).
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: root.showArtistColumn && LibraryTrackColumnState.artistVisible
            Layout.preferredWidth: LibraryTrackColumnState.artistWidth
            label: qsTr("ARTIST")
            columnKey: "artist"
            columnWidth: LibraryTrackColumnState.artistWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: root.showAlbumColumn && LibraryTrackColumnState.albumVisible
            Layout.preferredWidth: LibraryTrackColumnState.albumWidth
            label: qsTr("ALBUM")
            columnKey: "album"
            columnWidth: LibraryTrackColumnState.albumWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.formatVisible
            Layout.preferredWidth: LibraryTrackColumnState.formatWidth
            label: qsTr("FORMAT")
            columnKey: "format"
            columnWidth: LibraryTrackColumnState.formatWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.sampleRateVisible
            Layout.preferredWidth: LibraryTrackColumnState.sampleRateWidth
            label: qsTr("SAMPLE RATE")
            columnKey: "sampleRate"
            columnWidth: LibraryTrackColumnState.sampleRateWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.bitDepthVisible
            Layout.preferredWidth: LibraryTrackColumnState.bitDepthWidth
            label: qsTr("BIT DEPTH")
            columnKey: "bitDepth"
            columnWidth: LibraryTrackColumnState.bitDepthWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.dsdRateVisible
            Layout.preferredWidth: LibraryTrackColumnState.dsdRateWidth
            label: qsTr("DSD RATE")
            columnKey: "dsdRate"
            columnWidth: LibraryTrackColumnState.dsdRateWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.bitrateVisible
            Layout.preferredWidth: LibraryTrackColumnState.bitrateWidth
            label: qsTr("BITRATE")
            columnKey: "bitrate"
            columnWidth: LibraryTrackColumnState.bitrateWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.channelsVisible
            Layout.preferredWidth: LibraryTrackColumnState.channelsWidth
            label: qsTr("CHANNELS")
            columnKey: "channels"
            columnWidth: LibraryTrackColumnState.channelsWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.fileSizeVisible
            Layout.preferredWidth: LibraryTrackColumnState.fileSizeWidth
            label: qsTr("FILE SIZE")
            columnKey: "fileSize"
            columnWidth: LibraryTrackColumnState.fileSizeWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.genreVisible
            Layout.preferredWidth: LibraryTrackColumnState.genreWidth
            label: qsTr("GENRE")
            columnKey: "genre"
            columnWidth: LibraryTrackColumnState.genreWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.composerVisible
            Layout.preferredWidth: LibraryTrackColumnState.composerWidth
            label: qsTr("COMPOSER")
            columnKey: "composer"
            columnWidth: LibraryTrackColumnState.composerWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.yearVisible
            Layout.preferredWidth: LibraryTrackColumnState.yearWidth
            label: qsTr("YEAR")
            columnKey: "year"
            columnWidth: LibraryTrackColumnState.yearWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.durationVisible
            Layout.preferredWidth: LibraryTrackColumnState.durationWidth
            label: qsTr("DURATION")
            columnKey: "duration"
            columnWidth: LibraryTrackColumnState.durationWidth
            sortable: root.columnSortable(columnKey)
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        ResizableHeaderCell {
            visible: root.showActions && LibraryTrackColumnState.actionsVisible
            Layout.preferredWidth: LibraryTrackColumnState.actionsWidth
            label: ""
            columnKey: "actions"
            columnWidth: LibraryTrackColumnState.actionsWidth
            resizable: false
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
            onContextRequested: column => root.openColumnContext(column)
        }
        // LIB-A P2-A §36: el contexto GLOBAL vive en la región vacía del
        // layout (Item hermano, no ancestro) — el right-click de una cell
        // NUNCA compite con el global (sin doble-open ni overwrite).
        Item {
            objectName: "headerEmptyRegion"
            Layout.fillWidth: true
            Layout.minimumWidth: MichiSpacing.md
            TapHandler {
                acceptedButtons: Qt.RightButton
                onTapped: {
                    MichiAccessibility.notePointer()
                    root.openGlobalContext()
                }
            }
        }
    }

    // LIB-A §11/12/14: DOS intents contextuales — cell (targetColumn
    // exacto con sort explícito) y región vacía (configuración global).
    function openColumnContext(column) {
        if (column.length === 0)
            return
        headerContextMenu.targetColumn = column
        headerContextMenu.targetLabel = headerContextMenu.columnLabel(column)
        headerContextMenu.targetSortable = root.sortingEnabled
            && LibraryTrackColumnState.sortableColumns.indexOf(column) !== -1
        headerContextMenu.open()
    }

    function openGlobalContext() {
        headerContextMenu.targetColumn = ""
        headerContextMenu.targetLabel = ""
        headerContextMenu.targetSortable = false
        headerContextMenu.open()
    }

    // LIB-A P2-B: UNA predicción de columnas sortables (aplicación +
    // singleton) — nunca conocimiento duplicado por cell.
    function columnSortable(column) {
        return root.sortingEnabled
            && LibraryTrackColumnState.sortableColumns.indexOf(column) !== -1
    }

    TrackTableHeaderContextMenu {
        id: headerContextMenu

        onSortAscendingRequested: column =>
            root.sortDirectionRequested(column, false)
        onSortDescendingRequested: column =>
            root.sortDirectionRequested(column, true)
        onHideColumnRequested: column =>
            LibraryTrackColumnState.setVisible(column, false)
        onResetWidthRequested: column =>
            LibraryTrackColumnState.resetWidth(column)
        onPresetRequested: name => LibraryTrackColumnState.applyPreset(name)
        onToggleColumnRequested: column => {
            // Title está locked en el singleton (no-op defensivo).
            LibraryTrackColumnState.setVisible(
                column, !LibraryTrackColumnState.isVisible(column))
        }
        onResetWidthsRequested: LibraryTrackColumnState.resetWidths()
        onRestoreDefaultsRequested: LibraryTrackColumnState.restoreDefaults()
    }
}
