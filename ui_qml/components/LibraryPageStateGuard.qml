import QtQuick
import "../theme"

Item {
    id: root

    property var bridge: null
    property bool loading: false
    property bool empty: false
    property bool hasError: false
    property string errorMessage: ""
    property string emptyMessage: "No hay elementos"
    property string loadingMessage: "Cargando\u2026"

    default property alias content: contentArea.children

    Item {
        id: contentArea
        anchors.fill: parent
        visible: !root.loading && !root.hasError && !root.empty
    }

    Item {
        anchors.fill: parent
        visible: root.loading

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.loadingMessage
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }

    Item {
        anchors.fill: parent
        visible: root.hasError && !root.loading

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "\u26A0 Error"
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                Accessible.role: Accessible.Icon
                Accessible.name: "Error"
                Accessible.description: root.errorMessage
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.errorMessage
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width * 0.8
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Item {
        anchors.fill: parent
        visible: root.empty && !root.loading && !root.hasError

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.emptyMessage
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
