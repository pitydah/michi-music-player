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
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.titleVisible
            Layout.preferredWidth: root.titleColumnWidth
            label: qsTr("TITLE")
            columnKey: "title"
            columnWidth: root.titleColumnWidth
            resizeBaseWidth: LibraryTrackColumnState.titleWidth
            sortable: root.sortingEnabled
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
        }
        ResizableHeaderCell {
            visible: root.showArtistColumn && LibraryTrackColumnState.artistVisible
            Layout.preferredWidth: LibraryTrackColumnState.artistWidth
            label: qsTr("ARTIST")
            columnKey: "artist"
            columnWidth: LibraryTrackColumnState.artistWidth
            sortable: root.sortingEnabled
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: root.showAlbumColumn && LibraryTrackColumnState.albumVisible
            Layout.preferredWidth: LibraryTrackColumnState.albumWidth
            label: qsTr("ALBUM")
            columnKey: "album"
            columnWidth: LibraryTrackColumnState.albumWidth
            sortable: root.sortingEnabled
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.formatVisible
            Layout.preferredWidth: LibraryTrackColumnState.formatWidth
            label: qsTr("FORMAT")
            columnKey: "format"
            columnWidth: LibraryTrackColumnState.formatWidth
            sortable: root.sortingEnabled
            sortActive: root.sortColumn === columnKey
            sortDescending: root.sortDescending
            onSortRequested: column => root.sortRequested(column)
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.sampleRateVisible
            Layout.preferredWidth: LibraryTrackColumnState.sampleRateWidth
            label: qsTr("SAMPLE RATE")
            columnKey: "sampleRate"
            columnWidth: LibraryTrackColumnState.sampleRateWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.bitDepthVisible
            Layout.preferredWidth: LibraryTrackColumnState.bitDepthWidth
            label: qsTr("BIT DEPTH")
            columnKey: "bitDepth"
            columnWidth: LibraryTrackColumnState.bitDepthWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.dsdRateVisible
            Layout.preferredWidth: LibraryTrackColumnState.dsdRateWidth
            label: qsTr("DSD RATE")
            columnKey: "dsdRate"
            columnWidth: LibraryTrackColumnState.dsdRateWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.bitrateVisible
            Layout.preferredWidth: LibraryTrackColumnState.bitrateWidth
            label: qsTr("BITRATE")
            columnKey: "bitrate"
            columnWidth: LibraryTrackColumnState.bitrateWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.channelsVisible
            Layout.preferredWidth: LibraryTrackColumnState.channelsWidth
            label: qsTr("CHANNELS")
            columnKey: "channels"
            columnWidth: LibraryTrackColumnState.channelsWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.fileSizeVisible
            Layout.preferredWidth: LibraryTrackColumnState.fileSizeWidth
            label: qsTr("FILE SIZE")
            columnKey: "fileSize"
            columnWidth: LibraryTrackColumnState.fileSizeWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.genreVisible
            Layout.preferredWidth: LibraryTrackColumnState.genreWidth
            label: qsTr("GENRE")
            columnKey: "genre"
            columnWidth: LibraryTrackColumnState.genreWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.composerVisible
            Layout.preferredWidth: LibraryTrackColumnState.composerWidth
            label: qsTr("COMPOSER")
            columnKey: "composer"
            columnWidth: LibraryTrackColumnState.composerWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.yearVisible
            Layout.preferredWidth: LibraryTrackColumnState.yearWidth
            label: qsTr("YEAR")
            columnKey: "year"
            columnWidth: LibraryTrackColumnState.yearWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
        }
        ResizableHeaderCell {
            visible: LibraryTrackColumnState.durationVisible
            Layout.preferredWidth: LibraryTrackColumnState.durationWidth
            label: qsTr("DURATION")
            columnKey: "duration"
            columnWidth: LibraryTrackColumnState.durationWidth
            onResizeRequested: (column, width) => root.resizeColumn(column, width)
            onResetRequested: column => LibraryTrackColumnState.resetWidth(column)
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
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            MichiAccessibility.notePointer()
            columnsMenu.popup()
        }
    }

    MichiMenu {
        id: columnsMenu
        title: qsTr("Columns")

        MenuItem { text: qsTr("Artwork"); checkable: true; checked: LibraryTrackColumnState.artworkVisible; onTriggered: LibraryTrackColumnState.artworkVisible = checked }
        MenuItem { text: qsTr("Title"); checkable: true; checked: LibraryTrackColumnState.titleVisible; onTriggered: LibraryTrackColumnState.titleVisible = checked }
        MenuItem { text: qsTr("Artist"); checkable: true; checked: LibraryTrackColumnState.artistVisible; onTriggered: LibraryTrackColumnState.artistVisible = checked }
        MenuItem { text: qsTr("Album"); checkable: true; checked: LibraryTrackColumnState.albumVisible; onTriggered: LibraryTrackColumnState.albumVisible = checked }
        MenuItem { text: qsTr("Format"); checkable: true; checked: LibraryTrackColumnState.formatVisible; onTriggered: LibraryTrackColumnState.formatVisible = checked }
        MenuItem { text: qsTr("Sample Rate"); checkable: true; checked: LibraryTrackColumnState.sampleRateVisible; onTriggered: LibraryTrackColumnState.sampleRateVisible = checked }
        MenuItem { text: qsTr("Bit Depth"); checkable: true; checked: LibraryTrackColumnState.bitDepthVisible; onTriggered: LibraryTrackColumnState.bitDepthVisible = checked }
        MenuItem { text: qsTr("DSD Rate"); checkable: true; checked: LibraryTrackColumnState.dsdRateVisible; onTriggered: LibraryTrackColumnState.dsdRateVisible = checked }
        MenuItem { text: qsTr("Bitrate"); checkable: true; checked: LibraryTrackColumnState.bitrateVisible; onTriggered: LibraryTrackColumnState.bitrateVisible = checked }
        MenuItem { text: qsTr("Channels"); checkable: true; checked: LibraryTrackColumnState.channelsVisible; onTriggered: LibraryTrackColumnState.channelsVisible = checked }
        MenuItem { text: qsTr("File Size"); checkable: true; checked: LibraryTrackColumnState.fileSizeVisible; onTriggered: LibraryTrackColumnState.fileSizeVisible = checked }
        MenuItem { text: qsTr("Genre"); checkable: true; checked: LibraryTrackColumnState.genreVisible; onTriggered: LibraryTrackColumnState.genreVisible = checked }
        MenuItem { text: qsTr("Composer"); checkable: true; checked: LibraryTrackColumnState.composerVisible; onTriggered: LibraryTrackColumnState.composerVisible = checked }
        MenuItem { text: qsTr("Year"); checkable: true; checked: LibraryTrackColumnState.yearVisible; onTriggered: LibraryTrackColumnState.yearVisible = checked }
        MenuItem { text: qsTr("Duration"); checkable: true; checked: LibraryTrackColumnState.durationVisible; onTriggered: LibraryTrackColumnState.durationVisible = checked }
        MichiSeparator { }
        MenuItem { text: qsTr("Reset Column Widths"); onTriggered: LibraryTrackColumnState.resetWidths() }
        MenuItem { text: qsTr("Restore Default Columns"); onTriggered: LibraryTrackColumnState.restoreDefaultColumns() }
    }
}
