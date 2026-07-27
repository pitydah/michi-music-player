import QtQuick
import "../../components"

MichiPage {
    id: root

    property string sectionTitle: ""
    property string sectionSubtitle: ""
    property string sectionIcon: "library"
    property int navigationIndex: 0
    property bool embedded: false
    property bool standardFiltersEnabled: false
    property bool headerContextEnabled: !embedded
    property bool headerSearchEnabled: true
    property string headerSearchText: ""
    property string headerSearchPlaceholder: sectionTitle !== ""
                                             ? qsTr("Buscar en %1…").arg(sectionTitle.toLowerCase())
                                             : qsTr("Buscar en Biblioteca…")
    property var headerViewModes: []
    property int headerCurrentView: 0
    property bool headerFilterEnabled: standardFiltersEnabled && !embedded
    property int headerFilterCount: standardFilterPopover.activeFilterCount
    property bool headerRefreshEnabled: true
    property bool headerLoading: false
    property string headerStatusText: ""

    accessibleName: sectionTitle
    scrollable: false
    constrainContentWidth: false

    function openHeaderFilters() {
        if (root.headerFilterEnabled)
            standardFilterPopover.open()
    }

    header: LibraryNavigationBar {
        width: parent ? parent.width : 0
        visible: !root.embedded
        height: visible ? implicitHeight : 0
        currentIndex: root.navigationIndex
        onSectionRequested: function(index, route) {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate(route)
        }
    }

    LibraryFilterPopover {
        id: standardFilterPopover
        width: 0
        height: 0
        onFormatFilterChanged: function(format) {
            if (standardFilterPopover.lib)
                standardFilterPopover.lib.setFormatFilter(format)
        }
        onGenreFilterChanged: function(genre) {
            if (standardFilterPopover.lib)
                standardFilterPopover.lib.setGenreFilter(genre)
        }
        onComposerFilterChanged: function(composer) {
            if (standardFilterPopover.lib)
                standardFilterPopover.lib.setComposerFilter(composer)
        }
        onYearFilterChanged: function(year) {
            if (standardFilterPopover.lib)
                standardFilterPopover.lib.setYearFilter(year)
        }
    }
}
