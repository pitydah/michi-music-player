import QtQuick
import QtQuick.Controls
import "../../theme"
import ".."
import "../foundations"

FocusScope {
    id: root

    property string trackId: ""
    property string publicRef: ""
    property string title: ""
    property string artist: ""
    property string album: ""
    property string duration: ""
    property string format: ""
    property url coverSource: ""
    property bool selected: false
    property bool current: false

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitHeight: MichiTheme.rowHeightComfortable
    activeFocusOnTab: enabled
    opacity: enabled ? 1.0 : MichiTheme.disabledOpacity

    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist !== "" ? ", " + artist : "")
    Accessible.description: current ? "Pista actual" : album
    Accessible.selected: selected

    Keys.onReturnPressed: root.primaryActionRequested()
    Keys.onSpacePressed: root.primaryActionRequested()

    Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Track Row"
    objectName: "michiTrackRow"
    focus: true
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: root.selected ? MichiTheme.colors.accentSelection
                             : hover.hovered ? MichiTheme.colors.surfaceHover : "transparent"
    }
    Image {
        id: cover
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: MichiTheme.coverSizeSmall
        height: width
        source: root.coverSource
        fillMode: Image.PreserveAspectCrop
        visible: source.toString() !== ""
    }
    MichiIcon {
        anchors.fill: cover
        iconName: "library"
        visible: !cover.visible
        accessibleName: "Sin portada"
    }
    Column {
        anchors.left: cover.right
        anchors.right: meta.left
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        anchors.verticalCenter: parent.verticalCenter
        Text { width: parent.width; text: root.title; color: root.current ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary; elide: Text.ElideRight }
        Text { width: parent.width; text: root.artist + (root.album !== "" ? " · " + root.album : ""); color: MichiTheme.colors.textSecondary; elide: Text.ElideRight }
    }
    Text {
        id: meta
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: [root.format, root.duration].filter(function(value) { return value !== "" }).join(" · ")
        color: MichiTheme.colors.textMuted
    }
    MichiFocusRing { control: root; controlRadius: MichiTheme.radiusSm }
    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked(); onDoubleTapped: root.doubleClicked() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: function(point) { root.contextRequested(point.position.x, point.position.y) } }
}
