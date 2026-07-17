import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property var model: []
    property int currentIndex: -1
    property string currentText: ""
    property string placeholderText: "Seleccionar..."
    property bool loading: false
    property bool popupOpen: false
    property string textRole: ""
    property string accessibleName: root.placeholderText
    property string accessibleDescription: ""

    signal activated(int index)
    implicitHeight: MichiTheme.minimumInteractiveSize
    implicitWidth: 200
    activeFocusOnTab: enabled && visible

    Accessible.role: Accessible.ComboBox
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    function _modelLength() {
        if (root.model === null || root.model === undefined) return 0
        if (typeof root.model === 'object' && root.model.count !== undefined) return root.model.count
        return root.model.length || 0
    }

    function _modelGet(idx) {
        if (root.model === null || root.model === undefined) return undefined
        if (typeof root.model === 'object' && root.model.get !== undefined) return root.model.get(idx)
        return root.model[idx]
    }

    onCurrentIndexChanged: {
        if (root.currentIndex >= 0 && root.currentIndex < root._modelLength()) {
            var item = root._modelGet(root.currentIndex)
            root.currentText = typeof item === "object" ? (item.text || item.name || "") : (item !== undefined ? String(item) : "")
        } else {
            root.currentText = ""
        }
    }

    Rectangle {
        id: trigger
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        color: root.loading ? MichiTheme.colors.surfaceDisabled : MichiTheme.colors.surfaceInput
        border.width: root.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
        border.color: root.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

        Text {
            anchors.left: parent.left
            anchors.leftMargin: MichiTheme.spacing.md
            anchors.right: arrow.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.currentText !== "" ? root.currentText : root.placeholderText
            color: root.currentText !== "" ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            elide: Text.ElideRight
        }

        Text {
            id: arrow
            anchors.right: parent.right
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.verticalCenter: parent.verticalCenter
            text: "\u25BE"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
        }

        MouseArea {
            anchors.fill: parent
            enabled: !root.loading
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.forceActiveFocus()
                root.popupOpen = !root.popupOpen
            }
        }
    }

    Rectangle {
        id: dropdown
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: trigger.bottom
        anchors.topMargin: MichiTheme.spacing.xxs
        visible: root.popupOpen && !root.loading
        radius: MichiTheme.radius.sm
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        z: 1000

        ListView {
            id: listView
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xxs
            model: root.model
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            currentIndex: root.currentIndex
            highlightMoveDuration: 0

            delegate: Item {
                width: parent.width
                height: MichiTheme.rowHeightCompact
                property bool isSelected: index === root.currentIndex
                property bool isHovered: delegateMa.containsMouse

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radius.xs
                    color: isSelected ? MichiTheme.colors.accentSelection
                         : isHovered ? MichiTheme.colors.surfaceHover : "transparent"
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: MichiTheme.spacing.md
                    anchors.verticalCenter: parent.verticalCenter
                    text: {
                        if (root.textRole && typeof modelData === "object")
                            return modelData[root.textRole] || ""
                        return typeof modelData === "object" ? (modelData.text || modelData.name || "") : modelData
                    }
                    color: root.currentIndex === index ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: root.currentIndex === index ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }

                MouseArea {
                    id: delegateMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.currentIndex = index
                        root.popupOpen = false
                        root.activated(index)
                    }
                }

                Keys.onReturnPressed: {
                    root.currentIndex = index
                    root.popupOpen = false
                    root.activated(index)
                }

                Keys.onEnterPressed: {
                    root.currentIndex = index
                    root.popupOpen = false
                    root.activated(index)
                }
            }
        }

        height: Math.min(root._modelLength() * MichiTheme.rowHeightCompact + MichiTheme.spacing.xxs * 2, 300)
    }

    Keys.onUpPressed: function(event) {
        if (root.popupOpen) {
            var prev = Math.max(0, root.currentIndex - 1)
            root.currentIndex = prev
            listView.positionViewAtIndex(root.currentIndex, ListView.Contain)
            event.accepted = true
        }
    }

    Keys.onDownPressed: function(event) {
        if (root.popupOpen) {
            var next = Math.min(root._modelLength() - 1, root.currentIndex + 1)
            root.currentIndex = next
            listView.positionViewAtIndex(root.currentIndex, ListView.Contain)
            event.accepted = true
        } else {
            root.popupOpen = true
            event.accepted = true
        }
    }

    Keys.onReturnPressed: function(event) {
        if (root.popupOpen) {
            root.activated(root.currentIndex)
            root.popupOpen = false
            event.accepted = true
        }
    }

    Keys.onEnterPressed: function(event) {
        if (root.popupOpen) {
            root.activated(root.currentIndex)
            root.popupOpen = false
            event.accepted = true
        }
    }

    Keys.onEscapePressed: function(event) {
        if (root.popupOpen) {
            root.popupOpen = false
            event.accepted = true
        }
    }

    onActiveFocusChanged: {
        if (!root.activeFocus)
            root.popupOpen = false
    }
}
