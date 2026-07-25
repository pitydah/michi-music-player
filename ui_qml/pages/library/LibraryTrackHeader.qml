import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Track Header"
    objectName: "libraryTrackHeader"
    focus: true
    id: root
    width: parent.width; height: 36

    MichiResponsive { id: responsive; availableWidth: root.width }

    property var bridge: null
    property string sortKey: "title"
    property bool sortAsc: true

    color: MichiTheme.colors.surfaceCard

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: 0

        Item { width: 20; height: 1 }

        Item { width: 30; height: 1 }

        HeaderCell { Layout.fillWidth: true; label: qsTr("Título"); sortField: "title" }
        HeaderCell { Layout.preferredWidth: responsive.compact ? 120 : 160; label: qsTr("Artista"); sortField: "artist" }
        HeaderCell { Layout.preferredWidth: responsive.compact ? 120 : 160; label: qsTr("Álbum"); sortField: "album" }
        HeaderCell { visible: !responsive.compact; Layout.preferredWidth: 40; label: qsTr("Cal.") }
        HeaderCell { visible: !responsive.compact; Layout.preferredWidth: 40; label: qsTr("Año"); sortField: "year"; alignRight: true }
        HeaderCell { visible: !responsive.compact; Layout.preferredWidth: 48; label: qsTr("Dur."); sortField: "duration"; alignRight: true }
    }

    component HeaderCell: Item {
        property string label: ""
        property string sortField: ""
        property bool alignRight: false
        height: parent ? parent.height : 36
        Text {
            anchors.fill: parent
            text: parent.label
            color: root.bridge && root.bridge.activeSortKey === parent.sortField
                   ? MichiTheme.colors.accentPrimary : MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: root.bridge && root.bridge.activeSortKey === parent.sortField
                         ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightMedium
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: parent.alignRight ? Text.AlignRight : Text.AlignLeft
            elide: Text.ElideRight
        }
        MouseArea {
            anchors.fill: parent
            enabled: parent.sortField !== ""
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: if (root.bridge && typeof root.bridge.sortBy !== "undefined") root.bridge.sortBy(parent.sortField)
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width; height: 1
        color: MichiTheme.colors.borderSubtle
    }
}
