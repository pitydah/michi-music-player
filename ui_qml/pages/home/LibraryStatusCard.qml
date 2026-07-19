import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Status Card"
    objectName: "libraryStatusCard"
    focus: true
    id: root

    property int albums: 0
    property int artists: 0
    property int tracks: 0
    property bool hasData: false

    signal openLibrary()

    implicitHeight: 190

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radius.md

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openLibrary()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: qsTr("Biblioteca")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: root.hasData ? statsComponent : emptyComponent
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true
                Layout.alignment: Qt.AlignLeft
                text: qsTr("Explorar biblioteca")
                variant: "secondary"
                onClicked: root.openLibrary()
            }
        }
    }

    Component {
        id: statsComponent
        RowLayout {
            width: parent ? parent.width : implicitWidth
            spacing: MichiTheme.spacing.xl
            Column {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs
                Text {
                    text: root.albums
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Text {
                    text: qsTr("Álbumes")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
            Column {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs
                Text {
                    text: root.artists
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Text {
                    text: qsTr("Artistas")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
            Column {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs
                Text {
                    text: root.tracks
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
                Text {
                    text: qsTr("Canciones")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }

    Component {
        id: emptyComponent
        Text {
            text: qsTr("Biblioteca no indexada. Agrega carpetas con música para comenzar.")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            width: parent.width
            wrapMode: Text.WordWrap
        }
    }
}
