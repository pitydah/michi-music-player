import QtQuick
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

    implicitHeight: 160

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

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: qsTr("Biblioteca")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Loader {
                sourceComponent: root.hasData ? statsComponent : emptyComponent
                width: parent.width
            }

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: qsTr("Explorar biblioteca")
                variant: "secondary"
                onClicked: root.openLibrary()
            }
        }
    }

    Component {
        id: statsComponent
        Row {
            spacing: MichiTheme.spacing.xl
            Column {
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
