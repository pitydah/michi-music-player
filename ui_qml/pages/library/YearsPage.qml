import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

LibrarySectionPage {
    objectName: "yearsPage"
    focus: true
    id: root
    sectionTitle: qsTr("Años y décadas")
    sectionSubtitle: qsTr("Explora la colección cronológicamente")
    sectionIcon: "albums"
    navigationIndex: 6

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _years: []

    signal yearSelected(string year)

    function reload() {
        if (root.lib && root.lib.getYears) {
            root._years = root.lib.getYears() || []
        }
    }

    function openYear(year) {
        root.yearSelected(String(year))
        if (root.lib && root.lib.setYearFilter)
            root.lib.setYearFilter(String(year))
        if (typeof navigationBridge !== "undefined")
            navigationBridge.navigate("library")
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            Text {
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: MichiTheme.spacing.md
                text: qsTr("Años")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }
        }

        Flow {
            Layout.fillWidth: true; Layout.fillHeight: true
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: root._years

                Rectangle {
                    width: 80; height: 60; radius: MichiTheme.radius.sm
                    color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard
                    activeFocusOnTab: true
                    border.width: activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                    border.color: activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

                    Column {
                        anchors.centerIn: parent; spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: typeof modelData === "object" ? (modelData.year || modelData.name) : modelData
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: typeof modelData === "object" && modelData.count ? modelData.count + "" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }
                    }

                    MouseArea {
                        id: mouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.openYear(typeof modelData === "object" ? (modelData.year || modelData.name) : modelData)
                    }

                    Keys.onReturnPressed: root.openYear(typeof modelData === "object" ? (modelData.year || modelData.name) : modelData)
                    Keys.onEnterPressed: root.openYear(typeof modelData === "object" ? (modelData.year || modelData.name) : modelData)
                    Keys.onSpacePressed: root.openYear(typeof modelData === "object" ? (modelData.year || modelData.name) : modelData)
                }
            }
        }
    }
}
