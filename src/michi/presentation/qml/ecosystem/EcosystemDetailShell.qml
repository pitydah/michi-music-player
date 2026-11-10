import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// Shared product-level detail shell. Device pages provide domain content;
// this component provides Player-native hierarchy, responsive actions and a
// separated danger zone.
Item {
    id: root
    default property alias contentData: contentLayout.data

    property string eyebrow: ""
    property string title: ""
    property string subtitle: ""
    property string iconName: "device"
    property string statusText: ""
    property string statusTone: "neutral"
    property string primaryAction: ""
    property string secondaryAction: ""
    property bool primaryEnabled: true
    property bool secondaryEnabled: true
    property bool dangerVisible: false
    property bool dangerEnabled: true
    property string dangerTitle: qsTr("Zona de riesgo")
    property string dangerMessage: ""
    property string dangerAction: ""
    readonly property bool compact: MichiBreakpoints.isCompact(width)

    signal backRequested()
    signal primaryRequested()
    signal secondaryRequested()
    signal dangerRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.compact ? MichiSpacing.md : MichiSpacing.lg
        spacing: MichiSpacing.lg

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md

            MichiButton {
                iconName: "back"
                iconOnly: true
                variant: "ghost"
                accessibleName: qsTr("Volver")
                onClicked: root.backRequested()
            }

            MichiIcon {
                name: root.iconName
                iconColor: MichiPalette.auroraBlue
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs
                MichiText {
                    visible: root.eyebrow.length > 0
                    text: root.eyebrow
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.title
                    role: "display"
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
            }

            MichiStatusChip {
                visible: root.statusText.length > 0 && !root.compact
                text: root.statusText
                tone: root.statusTone
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: root.statusText.length > 0 && root.compact
            MichiStatusChip {
                text: root.statusText
                tone: root.statusTone
            }
            Item { Layout.fillWidth: true }
        }

        Flow {
            Layout.fillWidth: true
            visible: root.primaryAction.length > 0 || root.secondaryAction.length > 0
            spacing: MichiSpacing.sm
            layoutDirection: Qt.RightToLeft

            MichiButton {
                visible: root.primaryAction.length > 0
                text: root.primaryAction
                enabled: root.primaryEnabled
                onClicked: root.primaryRequested()
            }
            MichiButton {
                visible: root.secondaryAction.length > 0
                text: root.secondaryAction
                enabled: root.secondaryEnabled
                variant: "ghost"
                onClicked: root.secondaryRequested()
            }
        }

        MichiScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                id: contentLayout
                width: parent.width
                spacing: MichiSpacing.lg
            }
        }

        MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
            Layout.fillWidth: true
            visible: root.dangerVisible
            elevation: "subtle"
            accented: true
            accentColor: MichiPalette.error
            contentPadding: MichiSpacing.lg

            RowLayout {
                id: michiDetailsLayout1
                anchors.fill: parent
                spacing: MichiSpacing.lg
                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText { text: root.dangerTitle; role: "section"; color: MichiPalette.error }
                    MichiText {
                        visible: root.dangerMessage.length > 0
                        text: root.dangerMessage
                        role: "secondary"
                        wrapMode: Text.WordWrap
                    }
                }
                MichiButton {
                    visible: root.dangerAction.length > 0
                    text: root.dangerAction
                    enabled: root.dangerEnabled
                    variant: "danger"
                    onClicked: root.dangerRequested()
                }
            }
        }
    }
}
