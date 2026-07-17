import QtQuick
import QtQuick.Controls
import "../../theme"
import ".."
import "../foundations"

FocusScope {
    id: root

    property string albumId: ""
    property string publicRef: ""
    property string title: ""
    property string artist: ""
    property string year: ""
    property url coverSource: ""
    property bool selected: false

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitWidth: 176
    implicitHeight: 224
    activeFocusOnTab: enabled
    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist !== "" ? ", " + artist : "")
    Accessible.selected: selected
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle { anchors.fill: parent; radius: MichiTheme.radius.md; color: root.selected ? MichiTheme.colors.accentSelection : hover.hovered ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard }
    objectName: "michiAlbumTile"
    focus: true
    Image { id: cover; x: MichiTheme.spacing.md; y: x; width: parent.width - x * 2; height: width; source: root.coverSource; fillMode: Image.PreserveAspectCrop; visible: source.toString() !== "" }
    MichiIcon { anchors.fill: cover; iconName: "album"; visible: !cover.visible; accessibleName: "Sin portada" }
    Column {
        anchors.left: cover.left; anchors.right: cover.right; anchors.top: cover.bottom; anchors.topMargin: MichiTheme.spacing.sm
        Text { width: parent.width; text: root.title; color: MichiTheme.colors.textPrimary; elide: Text.ElideRight; font.weight: MichiTheme.typography.weightSemiBold }
        Text { width: parent.width; text: root.artist + (root.year !== "" ? " · " + root.year : ""); color: MichiTheme.colors.textSecondary; elide: Text.ElideRight }
    }
    MichiFocusRing { control: root; controlRadius: MichiTheme.radius.md }
    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked(); onDoubleTapped: root.doubleClicked() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: function(point) { root.contextRequested(point.position.x, point.position.y) } }
}
