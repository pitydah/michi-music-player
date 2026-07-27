import QtQuick

LibrarySectionPage {
    id: root
    objectName: "genresPage"
    focus: true
    sectionTitle: qsTr("Géneros")
    sectionSubtitle: qsTr("Explora la biblioteca por estilo musical")
    sectionIcon: "songs"
    navigationIndex: 3

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _genres: []
    property int currentView: 0
    readonly property var visibleGenres: root.filteredEntries(
                                                    root._genres,
                                                    root.headerSearchText
                                                )

    headerSearchPlaceholder: qsTr("Buscar géneros…")
    headerViewModes: [
        {
            id: "grid",
            icon: "../../icons/view/library-genre-grid.svg",
            label: qsTr("Mosaico de géneros"),
            description: qsTr("Tarjetas amplias con cantidad de canciones")
        },
        {
            id: "list",
            icon: "../../icons/view/library-list.svg",
            label: qsTr("Lista de géneros"),
            description: qsTr("Lectura compacta ordenada por nombre")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: qsTr("%1 géneros").arg(root.visibleGenres.length)

    signal genreSelected(string genre)

    function entryName(entry) {
        if (typeof entry !== "object")
            return entry || ""
        return entry.name || entry.genre || ""
    }

    function filteredEntries(entries, query) {
        var normalized = (query || "").trim().toLocaleLowerCase()
        if (normalized === "")
            return entries || []
        return (entries || []).filter(function(entry) {
            return root.entryName(entry).toLocaleLowerCase().indexOf(normalized) >= 0
        })
    }

    function reload() {
        if (root.lib && root.lib.getGenres)
            root._genres = root.lib.getGenres() || []
    }

    function openGenre(genre) {
        root.genreSelected(genre)
        if (typeof navigationBridge !== "undefined" && genre)
            navigationBridge.navigateWithParams(
                "library.genre_detail",
                {genre: genre}
            )
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
    }

    function applyHeaderView(index) {
        if (index >= 0 && index < root.headerViewModes.length)
            root.currentView = index
    }

    function refreshHeaderContext() {
        root.reload()
    }

    function routeEnter(route, params) {
        root.reload()
    }

    LibraryFacetView {
        anchors.fill: parent
        entries: root.visibleGenres
        currentView: root.currentView
        singularName: qsTr("género")
        pluralName: qsTr("géneros")
        iconKey: "songs"
        onEntryActivated: function(value) { root.openGenre(value) }
    }

    Component.onCompleted: reload()
}
