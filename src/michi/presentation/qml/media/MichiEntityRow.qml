import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property string iconName: "circle"
    property string title: ""
    property string subtitle: ""
    property string technical: ""
    property bool selected: false
    property bool interactive: true
    signal activated()

    implicitHeight: MichiThemeState.rowHeight
    radius: MichiRadius.sm
    color: root.selected ? MichiSemanticColors.surfaceSelected
        : hover.hovered && root.interactive ? MichiSemanticColors.surfaceHover
        : "transparent"
    border.width: root.selected ? 1 : 0
    border.color: MichiSemanticColors.auroraBorderSubtle
    activeFocusOnTab: root.interactive
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title + (root.subtitle.length > 0 ? ", " + root.subtitle : "")

    Keys.onEnterPressed: if (root.interactive) { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onReturnPressed: if (root.interactive) { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onSpacePressed: if (root.interactive) { MichiAccessibility.noteKeyboard(); root.activated() }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_PageDown) {
            MichiAccessibility.noteKeyboard()
            root.moveByPage(1)
            event.accepted = true
        } else if (event.key === Qt.Key_PageUp) {
            MichiAccessibility.noteKeyboard()
            root.moveByPage(-1)
            event.accepted = true
        }
    }

    function moveByPage(direction) {
        var view = root.ListView.view
        if (!view || view.count <= 0)
            return
        var pageSize = Math.max(1, Math.floor(view.height / root.height) - 1)
        view.currentIndex = Math.max(0, Math.min(view.count - 1,
            view.currentIndex + direction * pageSize))
        view.positionViewAtIndex(view.currentIndex, ListView.Contain)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        MichiIcon {
            name: root.iconName
            Layout.preferredWidth: MichiMetrics.iconSmall
            Layout.preferredHeight: MichiMetrics.iconSmall
            iconColor: root.selected ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }

        MichiText {
            Layout.preferredWidth: Math.min(320, root.width * 0.35)
            text: root.title
            role: "body"
            font.weight: root.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }

        MichiText {
            visible: root.subtitle.length > 0
            Layout.preferredWidth: Math.min(240, root.width * 0.25)
            text: root.subtitle
            role: "secondary"
            elide: Text.ElideRight
        }

        Item { Layout.fillWidth: true }

        MichiText {
            visible: root.technical.length > 0
            text: root.technical
            role: "technical"
            technical: true
            color: MichiThemeState.precisionMode ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
    }

    Rectangle {
        visible: !root.selected
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        height: 1
        color: MichiSemanticColors.borderSubtle
        opacity: hover.hovered ? 0 : 0.72
    }

    HoverHandler {
        id: hover
        enabled: root.interactive
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: root.interactive
        onTapped: {
            MichiAccessibility.notePointer()
            root.forceActiveFocus()
            root.activated()
        }
    }
    MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
    Behavior on color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
    // Smooth the 0↔1 border toggle instead of popping it
    Behavior on border.width {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.micro }
    }
}
