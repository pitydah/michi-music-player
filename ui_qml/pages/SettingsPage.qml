import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Item {
    id: root
    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property string selectedCategoryId: ""
    property var selectedCategory: null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    signal closeRequested()

    function openCategory(catId) {
        root.selectedCategoryId = catId
        root.selectedCategory = null
        var cats = root.bridge ? root.bridge.categories : []
        for (var i = 0; i < cats.length; i++) {
            if (cats[i].id === catId) {
                root.selectedCategory = cats[i]
                break
            }
        }
    }

    function searchCategories(query) {
        if (!query) return
        var cats = root.bridge ? root.bridge.categories : []
        for (var i = 0; i < cats.length; i++) {
            if (cats[i].title.toLowerCase().indexOf(query.toLowerCase()) >= 0) {
                root.openCategory(cats[i].id)
                return
            }
        }
    }

    function resetCategory(catId) {
        if (root.bridge && catId) {
            var result = root.bridge.resetValue(/* key not known at category level */)
        }
    }

    Component.onCompleted: {
        if (root.bridge && typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
    }

    // Desktop: split view
    RowLayout {
        anchors.fill: parent; spacing: 0

        // Left panel: category list
        Rectangle {
            Layout.preferredWidth: 240; Layout.fillHeight: true
            color: MichiTheme.colors.surfaceCard; visible: !root.selectedCategory

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

                SearchField {
                    Layout.fillWidth: true
                    placeholderText: "Buscar ajustes..."
                    onSearchTextChanged: root.searchCategories(text)
                }

                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2
                    model: root.bridge ? root.bridge.categories : []
                    delegate: Rectangle {
                        width: parent.width; height: 44; radius: MichiTheme.radius.sm
                        color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                        Accessible.name: modelData.title || ""

                        RowLayout {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                            Label { text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; Layout.fillWidth: true }
                            Label { text: ">"; visible: mouse.containsMouse; color: MichiTheme.colors.textSecondary }
                        }

                        MouseArea {
                            id: mouse; anchors.fill: parent; hoverEnabled: true
                            onClicked: root.openCategory(modelData.id)
                        }
                    }
                }
            }
        }

        // Right panel: category detail
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            color: "transparent"; visible: root.selectedCategory !== null

            ColumnLayout {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

                RowLayout {
                    Layout.fillWidth: true
                    MichiButton { text: "< Volver"; variant: "ghost"; onClicked: root.selectedCategory = null }
                    Label { text: root.selectedCategory ? root.selectedCategory.title : ""; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary; Layout.fillWidth: true }
                    MichiButton { text: "Restaurar"; variant: "ghost"; onClicked: { if (root.bridge) root.bridge.resetAll(); if (root.notif) root.notif.showMessage("Ajustes restaurados", "info") } }
                }

                SettingsCategoryPage {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    bridge: root.bridge
                    categoryData: root.selectedCategory
                }
            }
        }

        // Compact: full-width list
        Item { visible: false }
    }

    // Compact fallback for narrow windows
    ColumnLayout {
        anchors.fill: parent; spacing: 0; visible: root.width < 600
        RowLayout {
            Layout.fillWidth: true
            MichiButton { text: root.selectedCategory ? "< Volver" : ""; variant: "ghost"; visible: root.selectedCategory; onClicked: root.selectedCategory = null }
            Label { text: root.selectedCategory ? root.selectedCategory.title : "Ajustes"; font.pixelSize: MichiTheme.typography.pageTitleSize; color: MichiTheme.colors.textPrimary; Layout.fillWidth: true }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            sourceComponent: root.selectedCategory ? detailView : listView
        }
    }

    Component { id: listView
        ListView {
            clip: true; spacing: 2
            model: root.bridge ? root.bridge.categories : []
            delegate: GlassCard {
                width: parent.width; height: 56
                title: modelData.title || ""
                onClicked: root.openCategory(modelData.id)
            }
        }
    }

    Component { id: detailView
        SettingsCategoryPage {
            bridge: root.bridge; categoryData: root.selectedCategory
        }
    }
}
