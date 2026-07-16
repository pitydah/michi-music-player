import QtQuick
import QtQuick.Controls
import "../../theme"
import ".."
import "../foundations"

FocusScope {
    id: root

    property string artistId: ""
    property string publicRef: ""
    property string title: ""
    property string subtitle: ""
    property url coverSource: ""
    property bool selected: false

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)
    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitWidth: 176
    implicitHeight: 208
    activeFocusOnTab: enabled
    Accessible.role: Accessible.ListItem
    Accessible.name: title
    Accessible.description: subtitle
    Accessible.selected: selected
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle { anchors.fill: parent; radius: MichiTheme.radiusMd; color: root.selected ? MichiTheme.colors.accentSelection : hover.hovered ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard }
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Artist Tile"
    objectName: "michiArtistTile"
    focus: true
    Image { id: portrait; anchors.horizontalCenter: parent.horizontalCenter; y: MichiTheme.spacing.md; width: parent.width - MichiTheme.spacing.xl; height: width; source: root.coverSource; fillMode: Image.PreserveAspectCrop; visible: source.toString() !== "" }
    MichiIcon { anchors.fill: portrait; iconName: "artist"; rounded: true; visible: !portrait.visible; accessibleName: "Sin imagen de artista" }
    Column {
        anchors.left: portrait.left; anchors.right: portrait.right; anchors.top: portrait.bottom; anchors.topMargin: MichiTheme.spacing.sm
        Text { width: parent.width; text: root.title; color: MichiTheme.colors.textPrimary; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; font.weight: MichiTheme.typography.weightSemiBold }
        Text { width: parent.width; text: root.subtitle; color: MichiTheme.colors.textSecondary; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; visible: text !== "" }
    }
    MichiFocusRing { control: root; controlRadius: MichiTheme.radiusMd }
    HoverHandler { id: hover }
    TapHandler { onTapped: root.clicked(); onDoubleTapped: root.doubleClicked() }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: function(point) { root.contextRequested(point.position.x, point.position.y) } }
}
