pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MenuItem {
    id: root

    property string headline: ""
    property string supportingText: ""
    property string artworkPath: ""
    property string fallbackText: ""
    property bool portrait: false
    property bool showFormatBadge: false
    property string formatKey: "unknown"
    property string formatLabel: "UNKNOWN"

    enabled: false
    focusPolicy: Qt.NoFocus

    implicitWidth: 284
    implicitHeight: 60
    leftPadding: MichiSpacing.sm
    rightPadding: MichiSpacing.sm
    topPadding: MichiSpacing.xs
    bottomPadding: MichiSpacing.xs

    indicator: Item {
        implicitWidth: 0
        implicitHeight: 0
    }

    contentItem: RowLayout {
        spacing: MichiSpacing.sm

        Loader {
            Layout.preferredWidth: 38
            Layout.preferredHeight: 38
            sourceComponent: root.portrait ? portraitArtwork : squareArtwork
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            MichiText {
                Layout.fillWidth: true
                text: root.headline
                role: "body"
                font.weight: Font.DemiBold
                color: MichiPalette.textPrimary
                elide: Text.ElideRight
            }

            MichiText {
                Layout.fillWidth: true
                visible: text.length > 0
                text: root.supportingText
                role: "caption"
                color: MichiPalette.textSecondary
                elide: Text.ElideRight
            }
        }

        MichiFormatBadge {
            visible: root.showFormatBadge
            formatKey: root.formatKey
            displayLabel: root.formatLabel
        }
    }

    background: Item {
        implicitWidth: 284
        implicitHeight: 60
    }

    Component {
        id: squareArtwork
        Artwork {
            sourcePath: root.artworkPath
            fallbackText: root.fallbackText
            requestedSize: 76
        }
    }

    Component {
        id: portraitArtwork
        ArtistPortraitArtwork {
            sourcePath: root.artworkPath
            fallbackText: root.fallbackText
            requestedSize: 76
        }
    }
}
