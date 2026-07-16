import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root
    objectName: "settingsPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property string selectedCategoryId: ""
    property var selectedCategory: null
    property string selectedSectionId: ""
    property var selectedSection: null
    property var selectedEntry: null
    property string searchQuery: ""
    property var shownCategories: []
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    signal closeRequested()

    function openCategory(catId) {
        root.selectedCategoryId = catId
        root.selectedCategory = null
        root.selectedSectionId = ""
        root.selectedSection = null
        root.selectedEntry = null
        var cats = root.bridge ? root.bridge.categories : []
        for (var i = 0; i < cats.length; i++) {
            if (cats[i].id === catId) {
                root.selectedCategory = cats[i]
                break
            }
        }
    }

    function openSection(sectionId) {
        root.selectedSectionId = sectionId
        root.selectedSection = null
        root.selectedEntry = null
        if (!root.selectedCategory) return
        for (var i = 0; i < root.selectedCategory.sections.length; i++) {
            if (root.selectedCategory.sections[i].id === sectionId) {
                root.selectedSection = root.selectedCategory.sections[i]
                break
            }
        }
    }

    function openEntry(entryKey) {
        root.selectedEntry = null
        if (!root.selectedSection) return
        for (var i = 0; i < root.selectedSection.entries.length; i++) {
            if (root.selectedSection.entries[i].key === entryKey) {
                root.selectedEntry = root.selectedSection.entries[i]
                break
            }
        }
    }

    function searchCategories(query) {
        root.searchQuery = query
        if (!query || !root.bridge) {
            root.shownCategories = root.bridge ? root.bridge.categories : []
            return
        }
        var q = query.toLowerCase()
        var cats = root.bridge.categories
        var filtered = []
        for (var i = 0; i < cats.length; i++) {
            var cat = cats[i]
            var match = cat.title.toLowerCase().indexOf(q) >= 0
            if (!match && cat.sections) {
                for (var j = 0; j < cat.sections.length; j++) {
                    var sec = cat.sections[j]
                    if (sec.title.toLowerCase().indexOf(q) >= 0) {
                        match = true
                        break
                    }
                    if (sec.entries) {
                        for (var k = 0; k < sec.entries.length; k++) {
                            var ent = sec.entries[k]
                            if (ent.label.toLowerCase().indexOf(q) >= 0 ||
                                ent.key.toLowerCase().indexOf(q) >= 0) {
                                match = true
                                break
                            }
                        }
                        if (match) break
                    }
                }
            }
            if (match) filtered.push(cat)
        }
        root.shownCategories = filtered
    }

    function resetCategory(catId) {
        if (!root.bridge || !catId) return
        var cats = root.bridge.categories
        for (var i = 0; i < cats.length; i++) {
            if (cats[i].id === catId && cats[i].sections) {
                for (var j = 0; j < cats[i].sections.length; j++) {
                    var sec = cats[i].sections[j]
                    if (sec.entries) {
                        for (var k = 0; k < sec.entries.length; k++) {
                            root.bridge.resetValue(sec.entries[k].key)
                        }
                    }
                }
                if (root.notif) root.notif.showMessage("Categoría restaurada", "info")
                break
            }
        }
    }

    function resetAll() {
        if (root.bridge) {
            root.bridge.resetAll()
            if (root.notif) root.notif.showMessage("Todos los ajustes restaurados", "info")
        }
    }

    function back() {
        if (root.selectedEntry) {
            root.selectedEntry = null
        } else if (root.selectedSection) {
            root.selectedSection = null
            root.selectedSectionId = ""
        } else if (root.selectedCategory) {
            root.selectedCategory = null
            root.selectedCategoryId = ""
            root.selectedSection = null
            root.selectedSectionId = ""
            root.selectedEntry = null
        }
    }

    function hasChanges() {
        return false
    }

    Component.onCompleted: {
        root.shownCategories = root.bridge ? root.bridge.categories : []
        if (root.bridge && typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
    }

    function _backIfNoBreadcrumbs() {
        if (root.selectedEntry || root.selectedSection || root.selectedCategory) {
            root.back()
        }
    }

    // Desktop layout: width >= 900
    RowLayout {
        anchors.fill: parent; spacing: 0
        visible: root.width >= 900

        // Left panel: category list
        Rectangle {
            Layout.preferredWidth: 240; Layout.fillHeight: true
            color: MichiTheme.colors.surfaceCard

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                SearchField {
                    id: searchFieldDesktop
                    Layout.fillWidth: true
                    placeholderText: "Buscar ajustes..."
                    onSearchTextChanged: root.searchCategories(text)
                }

                ListView {
                    focusPolicy: Qt.StrongFocus
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2
                    model: root.shownCategories
                    delegate: Rectangle {
                        width: parent.width; height: 44; radius: MichiTheme.radius.sm
                        color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                        RowLayout {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                            Label {
                                text: modelData.title || ""
                                color: root.selectedCategoryId === modelData.id ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: root.selectedCategoryId === modelData.id ? Font.Bold : Font.Normal
                                Layout.fillWidth: true
                            }
                            Label {
                                text: ">"
                                visible: mouse.containsMouse || root.selectedCategoryId === modelData.id
                                color: MichiTheme.colors.textSecondary
                            }
                        }

                        MouseArea {
                            id: mouse; anchors.fill: parent; hoverEnabled: true
                            onClicked: root.openCategory(modelData.id)
                        }

                        Keys.onReturnPressed: root.openCategory(modelData.id)
                        Keys.onSpacePressed: root.openCategory(modelData.id)
                        focus: true
                        activeFocusOnTab: true
                    }
                    keyNavigationEnabled: true
                }

                Rectangle {
                    Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle
                }

                MichiButton {
                    Layout.fillWidth: true
                    text: "Restaurar todo"
                    variant: "danger"
                    visible: root.bridge !== null
                    onClicked: confirmResetDialog.open()
                }
            }
        }

        // Right panel: detail view
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

                // Breadcrumbs
                RowLayout {
                    Layout.fillWidth: true; spacing: MichiTheme.spacing.xs; visible: root.selectedCategory !== null
                    Label {
                        text: "Ajustes"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.captionSize
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.back()
                        }
                    }
                    Label { text: "/"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize; visible: root.selectedCategory !== null }
                    Label {
                        text: root.selectedCategory ? root.selectedCategory.title : ""
                        color: root.selectedSection ? MichiTheme.colors.textSecondary : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: root.selectedSection ? Font.Normal : Font.Bold
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: { root.selectedSection = null; root.selectedEntry = null }
                        }
                    }
                    Label {
                        text: "/"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize
                        visible: root.selectedSection !== null
                    }
                    Label {
                        text: root.selectedSection ? root.selectedSection.title : ""
                        color: root.selectedEntry ? MichiTheme.colors.textSecondary : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: root.selectedEntry ? Font.Normal : Font.Bold
                        visible: root.selectedSection !== null
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: { root.selectedEntry = null }
                        }
                    }
                    Label {
                        text: "/"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize
                        visible: root.selectedEntry !== null
                    }
                    Label {
                        text: root.selectedEntry ? root.selectedEntry.label : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: Font.Bold
                        visible: root.selectedEntry !== null
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; visible: root.selectedCategory !== null
                    MichiButton { text: "< Volver"; variant: "ghost"; onClicked: root.back(); Accessible.name: "Volver" }
                    Label {
                        text: root.selectedEntry ? root.selectedEntry.label :
                              root.selectedSection ? root.selectedSection.title :
                              root.selectedCategory ? root.selectedCategory.title : ""
                        font.pixelSize: root.selectedEntry ? MichiTheme.typography.bodySize : MichiTheme.typography.sectionTitleSize
                        color: MichiTheme.colors.textPrimary; Layout.fillWidth: true
                    }
                    MichiButton {
                        text: "Restaurar categoría"
                        variant: "ghost"
                        visible: root.selectedCategory !== null && root.selectedSection === null && root.selectedEntry === null
                        onClicked: root.resetCategory(root.selectedCategoryId)
                    }
                }

                ScrollView {
                    focusPolicy: Qt.StrongFocus
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true

                    Loader {
                        sourceComponent: {
                            if (root.selectedCategory === null) return desktopCategoryList
                            if (root.selectedEntry) return entryDetailView
                            if (root.selectedSection) return sectionDetailView
                            return categoryDetailView
                        }
                    }
                }
            }
        }
    }

    // Tablet layout: width >= 600 and < 900
    RowLayout {
        anchors.fill: parent; spacing: 0
        visible: root.width >= 600 && root.width < 900

        Rectangle {
            Layout.preferredWidth: root.selectedCategory === null ? parent.width : 200
            Layout.fillHeight: true
            color: MichiTheme.colors.surfaceCard
            visible: root.selectedCategory === null || root.width >= 700

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                SearchField {
                    Layout.fillWidth: true
                    placeholderText: "Buscar..."
                    onSearchTextChanged: root.searchCategories(text)
                }

                ListView {
                    focusPolicy: Qt.StrongFocus
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2
                    model: root.shownCategories
                    delegate: Rectangle {
                        width: parent.width; height: 44; radius: MichiTheme.radius.sm
                        color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"

                        RowLayout {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                            Label {
                                text: modelData.title || ""
                                color: root.selectedCategoryId === modelData.id ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Label {
                                text: ">"
                                visible: mouse.containsMouse || root.selectedCategoryId === modelData.id
                                color: MichiTheme.colors.textSecondary
                            }
                        }

                        MouseArea {
                            id: mouseT; anchors.fill: parent; hoverEnabled: true
                            onClicked: root.openCategory(modelData.id)
                        }
                        Keys.onReturnPressed: root.openCategory(modelData.id)
                        focus: true; activeFocusOnTab: true
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

                RowLayout {
                    Layout.fillWidth: true; visible: root.selectedCategory !== null
                    MichiButton { text: "< Volver"; variant: "ghost"; onClicked: root.back(); Accessible.name: "Volver" }
                    Label {
                        text: root.selectedEntry ? root.selectedEntry.label :
                              root.selectedSection ? root.selectedSection.title :
                              root.selectedCategory ? root.selectedCategory.title : ""
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        color: MichiTheme.colors.textPrimary; Layout.fillWidth: true
                    }
                }

                ScrollView {
                    focusPolicy: Qt.StrongFocus
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    Loader {
                        sourceComponent: {
                            if (root.selectedCategory === null) return tabletCategoryList
                            if (root.selectedEntry) return entryDetailView
                            if (root.selectedSection) return sectionDetailView
                            return categoryDetailView
                        }
                    }
                }
            }
        }
    }

    // Compact layout: width >= 400 and < 600
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        visible: root.width >= 400 && root.width < 600

        RowLayout {
            Layout.fillWidth: true; Layout.margins: MichiTheme.spacing.md
            MichiButton {
                text: "< Volver"
                variant: "ghost"
                visible: root.selectedCategory !== null
                onClicked: root.back()
            }
            Label {
                text: root.selectedEntry ? root.selectedEntry.label :
                      root.selectedSection ? root.selectedSection.title :
                      root.selectedCategory ? root.selectedCategory.title : "Ajustes"
                font.pixelSize: MichiTheme.typography.pageTitleSize
                color: MichiTheme.colors.textPrimary; Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }
        }

        SearchField {
            Layout.fillWidth: true; Layout.margins: MichiTheme.spacing.sm
            placeholderText: "Buscar..."
            visible: root.selectedCategory === null
            onSearchTextChanged: root.searchCategories(text)
        }

        ScrollView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            Loader {
                sourceComponent: {
                    if (root.selectedCategory === null) return compactList
                    if (root.selectedEntry) return entryDetailView
                    if (root.selectedSection) return sectionDetailView
                    return compactCategoryDetail
                }
            }
        }
    }

    // Narrow layout: width < 400
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        visible: root.width < 400

        RowLayout {
            Layout.fillWidth: true; Layout.margins: MichiTheme.spacing.sm
            MichiButton {
                text: "<"
                variant: "ghost"
                implicitWidth: 36
                visible: root.selectedCategory !== null
                onClicked: root.back()
            }
            Label {
                text: root.selectedEntry ? root.selectedEntry.label :
                      root.selectedSection ? root.selectedSection.title :
                      root.selectedCategory ? root.selectedCategory.title : "Ajustes"
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary; Layout.fillWidth: true
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        ScrollView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            Loader {
                sourceComponent: {
                    if (root.selectedCategory === null) return compactList
                    if (root.selectedEntry) return entryDetailView
                    if (root.selectedSection) return sectionDetailView
                    return compactCategoryDetail
                }
            }
        }
    }

    Component { id: desktopCategoryList
        ListView {
            focusPolicy: Qt.StrongFocus
            clip: true; spacing: 2
            model: root.shownCategories.length > 0 ? root.shownCategories : (root.bridge ? root.bridge.categories : [])
            delegate: GlassCard {
                width: parent ? parent.width : 0; height: 72
                title: modelData.title || ""
                subtitle: modelData.sections ? modelData.sections.length + " secciones" : ""
                onClicked: root.openCategory(modelData.id)
            }
        }
    }

    Component { id: tabletCategoryList
        ListView {
            focusPolicy: Qt.StrongFocus
            clip: true; spacing: 2
            model: root.shownCategories.length > 0 ? root.shownCategories : (root.bridge ? root.bridge.categories : [])
            delegate: GlassCard {
                width: parent ? parent.width : 0; height: 64
                title: modelData.title || ""
                onClicked: root.openCategory(modelData.id)
            }
        }
    }

    Component { id: categoryDetailView
        ColumnLayout {
            spacing: MichiTheme.spacing.md
            Repeater {
                model: root.selectedCategory ? root.selectedCategory.sections : []
                GlassCard {
                    Layout.fillWidth: true
                    title: modelData.title || ""
                    subtitle: modelData.entries ? modelData.entries.length + " ajustes" : ""
                    onClicked: root.openSection(modelData.id)
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component { id: sectionDetailView
        ColumnLayout {
            spacing: MichiTheme.spacing.sm
            Repeater {
                model: root.selectedSection ? root.selectedSection.entries : []
                SettingsRow {
                    Layout.fillWidth: true
                    entry: modelData
                    onClicked: root.openEntry(modelData.key)
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component { id: entryDetailView
        ColumnLayout {
            anchors.fill: parent; spacing: MichiTheme.spacing.md
            SettingsRow {
                Layout.fillWidth: true
                entry: root.selectedEntry
            }
            Item { Layout.fillHeight: true }
        }
    }

    Component { id: compactList
        ListView {
            focusPolicy: Qt.StrongFocus
            clip: true; spacing: 2
            model: root.shownCategories.length > 0 ? root.shownCategories : (root.bridge ? root.bridge.categories : [])
            delegate: GlassCard {
                width: parent ? parent.width : 0; height: 56
                title: modelData.title || ""
                onClicked: root.openCategory(modelData.id)
            }
        }
    }

    Component { id: compactCategoryDetail
        ListView {
            focusPolicy: Qt.StrongFocus
            clip: true; spacing: 2
            model: root.selectedCategory ? root.selectedCategory.sections : []
            delegate: GlassCard {
                width: parent ? parent.width : 0; height: 56
                title: modelData.title || ""
                onClicked: root.openSection(modelData.id)
            }
        }
    }

    ConfirmActionDialog {
        id: confirmResetDialog
        title: "Restaurar todos los ajustes"
        message: "¿Estás seguro de que deseas restaurar todos los ajustes a sus valores por defecto? Esta acción no puede deshacerse."
        onConfirmed: root.resetAll()
    }
}
