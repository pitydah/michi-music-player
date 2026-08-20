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
    activeFocusOnTab: root.interactive
    Accessible.role: Accessible.ListItem
    Accessible.name: root.title + (root.subtitle.length > 0 ? ", " + root.subtitle : "")

    Keys.onEnterPressed: if (root.interactive) root.activated()
    Keys.onReturnPressed: if (root.interactive) root.activated()
    Keys.onSpacePressed: if (root.interactive) root.activated()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        MichiIcon {
            name: root.iconName
            Layout.preferredWidth: MichiMetrics.iconSmall
            Layout.preferredHeight: MichiMetrics.iconSmall
            iconColor: root.selected ? MichiPalette.auroraBlue : MichiPalette.textMuted
        }

        MichiText {
            Layout.fillWidth: true
            text: root.title
            role: "body"
            elide: Text.ElideRight
        }

        MichiText {
            Layout.preferredWidth: Math.min(240, root.width * .34)
            text: root.subtitle
            role: "secondary"
            elide: Text.ElideRight
        }

        MichiText {
            visible: root.technical.length > 0
            text: root.technical
            role: "technical"
            technical: true
            color: MichiThemeState.precisionMode ? MichiPalette.auroraCyan : MichiPalette.textMuted
        }
    }

    HoverHandler {
        id: hover
        enabled: root.interactive
        cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: root.interactive
        onTapped: {
            root.forceActiveFocus()
            root.activated()
        }
    }
    MichiFocusRing { visualFocus: root.activeFocus }
}
