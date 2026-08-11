import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

ColumnLayout {
    id: root
    spacing: MichiTheme.space6

    property var trackNames: []
    property int currentIndex: -1
    property int count: 0
    property bool hasPrev: false
    property bool hasNext: false

    signal trackClicked(int index)
    signal clearClicked()
    signal previousRequested()
    signal nextRequested()

    Text {
        text: "Queue (" + root.count + ")"
        font.pixelSize: MichiTheme.fontSizeBodyLarge
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.textSecondary
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiTheme.space6
        MichiButton { text: "⏮ Prev"; variant: "ghost"; enabled: root.hasPrev; onClicked: root.previousRequested() }
        MichiButton { text: "Next ⏭"; variant: "ghost"; enabled: root.hasNext; onClicked: root.nextRequested() }
    }

    ListView {
        id: queueList
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: root.trackNames
        clip: true

        delegate: Rectangle {
            width: queueList.width
            height: MichiTheme.controlHeightSmall
            color: index === root.currentIndex ? MichiTheme.surfaceSelected : "transparent"
            radius: MichiTheme.radiusSmall
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left; anchors.leftMargin: MichiTheme.space8
                text: (index+1)+". "+modelData
                color: index === root.currentIndex ? MichiTheme.accent : MichiTheme.textSecondary
                font.pixelSize: MichiTheme.fontSizeCaption
                elide: Text.ElideRight
                width: parent.width - MichiTheme.space16
            }
            MouseArea {
                anchors.fill: parent
                onClicked: root.trackClicked(index)
            }
        }
    }

    MichiButton {
        Layout.alignment: Qt.AlignHCenter
        text: "Clear Queue"
        variant: "ghost"
        onClicked: root.clearClicked()
    }
}
