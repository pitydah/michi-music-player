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
    property int pageSize: 100
    property bool hasMore: false
    property bool loadingMore: false
    property int totalGenres: 0
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
    headerStatusText: root.totalGenres > root.visibleGenres.length && root.headerSearchText === ""
                      ? qsTr("%1 de %2 géneros").arg(root._genres.length).arg(root.totalGenres)
                      : qsTr("%1 géneros").arg(root.visibleGenres.length)

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
        root._genres = []
        root.hasMore = false
        root.totalGenres = 0
        root.fetchMore()
    }

    function fetchMore() {
        if (!root.lib || !root.lib.getGenres || root.loadingMore)
            return
        root.loadingMore = true
        var result = root.lib.getGenres(root._genres.length, root.pageSize) || {}
        var items = result.items || []
        root._genres = root._genres.concat(items)
        root.totalGenres = Number(result.total || root._genres.length)
        root.hasMore = Boolean(result.has_more)
        root.loadingMore = false
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
        hasMore: root.hasMore
        loadingMore: root.loadingMore
        onEntryActivated: function(value) { root.openGenre(value) }
        onFetchMoreRequested: root.fetchMore()
    }

    Component.onCompleted: reload()
}
