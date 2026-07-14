import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var suggestions: ["reciente", "favoritos", "nuevo", "jazzy", "relajante"]
    property var bridge: null

    signal suggestionClicked(string text)

    implicitHeight: 60

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Sugerencias"; width: parent.width }

        Flow {
            width: parent.width; spacing: MichiTheme.spacing.sm

            Repeater {
                model: root.suggestions

                MichiButton {
                    text: modelData; variant: "ghost"
                    onClicked: root.suggestionClicked(modelData)
                }
            }
        }
    }
}
