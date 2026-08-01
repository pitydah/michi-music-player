import QtQuick
import QtQuick.Layouts
import "../theme"
import "."
import "../materials"

/* PlannedFeaturePage — canonical template for planned / missing features.
 *
 * Honest by contract: it presents the product vision and the real feature
 * state (Planificado, Concepto de producto, Configuración requerida, ...).
 * It never simulates active functionality nor shows fake data.
 *
 * Pages provide narrative sections through the default `content` alias;
 * width them with `root.contentWidth` (see derived pages for examples).
 */
Item {
    id: root
    objectName: "plannedFeaturePage"
    focus: true

    property string featureTitle: ""
    property string featureDescription: ""
    property string featureIcon: "settings"
    property string featureState: "planned"
    property string statusLabel: qsTr("Planificado")
    property string statusKind: "info"
    property string primaryActionText: ""
    property string secondaryActionText: ""
    default property alias content: contentColumn.data

    readonly property real contentWidth: contentColumn.width

    signal primaryActionRequested()
    signal secondaryActionRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: featureTitle

    function routeEnter(route, params) {}
    function routeLeave(route, params) {}

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        contentHeight: column.height + MichiTheme.spacing.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            GlassMaterial {
                width: parent.width
                height: heroLayout.implicitHeight + MichiTheme.spacing.xl * 2
                variant: "hero"
                radius: MichiTheme.radius.lg

                ColumnLayout {
                    id: heroLayout
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.md

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.md

                        MichiIcon {
                            iconKey: root.featureIcon
                            size: 40
                            color: MichiTheme.colors.accentPrimary
                            active: true
                            accessibleName: root.featureTitle
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.xs

                            Text {
                                Layout.fillWidth: true
                                text: root.featureTitle
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.heroTitleSize
                                font.weight: MichiTheme.typography.weightSemiBold
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.featureDescription
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                wrapMode: Text.WordWrap
                                lineHeight: MichiTheme.typography.lineHeightBody
                                visible: text !== ""
                            }
                        }

                        StatusBadge {
                            Layout.alignment: Qt.AlignTop
                            text: root.statusLabel
                            kind: root.statusKind
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.sm
                        visible: root.primaryActionText !== "" || root.secondaryActionText !== ""

                        MichiButton {
                            text: root.primaryActionText
                            variant: "primary"
                            visible: root.primaryActionText !== ""
                            activeFocusOnTab: true
                            onClicked: root.primaryActionRequested()
                        }

                        MichiButton {
                            text: root.secondaryActionText
                            variant: "ghost"
                            visible: root.secondaryActionText !== ""
                            activeFocusOnTab: true
                            onClicked: root.secondaryActionRequested()
                        }
                    }
                }
            }

            Column {
                id: contentColumn
                width: parent.width
                spacing: MichiTheme.spacing.md
            }
        }
    }
}
