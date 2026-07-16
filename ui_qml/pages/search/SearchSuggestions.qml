import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Search Suggestions"
    objectName: "searchSuggestions"
    focus: true
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
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: modelData; variant: "ghost"
                    onClicked: root.suggestionClicked(modelData)
                }
            }
        }
    }
}
