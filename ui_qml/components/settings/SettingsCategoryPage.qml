import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Category"
    objectName: "settingsCategoryPage"
    focus: true
    id: root
    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property string categoryId: ""
    property var categoryData: null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    function loadCategory(catId) {
        root.categoryId = catId
        if (!root.bridge) return
        var cats = root.bridge.categories
        for (var i = 0; i < cats.length; i++) {
            if (cats[i].id === catId) {
                root.categoryData = cats[i]
                return
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

        Label { text: root.categoryData ? root.categoryData.title : ""; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary }

        Repeater {
            model: root.categoryData ? root.categoryData.sections : []

            ColumnLayout {
                Layout.fillWidth: true; spacing: MichiTheme.spacing.sm

                Label { text: modelData.title || ""; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium; color: MichiTheme.colors.textSecondary; topPadding: MichiTheme.spacing.md }

                Repeater {
                    model: modelData.entries || []
                    SettingsRow { entry: modelData }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle; Layout.topMargin: MichiTheme.spacing.sm }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
