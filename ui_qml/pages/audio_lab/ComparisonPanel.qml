import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    focus: true
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null

    objectName: "ComparisonPanel"
    Accessible.role: Accessible.Panel
    Accessible.name: "Panel de comparación"

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        SectionHeader { text: "Archivo de referencia"; width: parent.width; objectName: "compareRefHeader"; Accessible.name: "Archivo de referencia" }

        AudioInputSelection {
            id: refInput
            objectName: "comparisonRefInput"
        }

        SectionHeader { text: "Archivo a comparar"; width: parent.width; objectName: "compareTargetHeader"; Accessible.name: "Archivo a comparar" }

        AudioInputSelection {
            id: targetInput
            objectName: "comparisonTargetInput"
        }

        MichiButton {
            text: "Iniciar comparación"
            variant: "primary"
            enabled: refInput.selectedFiles.length > 0 && targetInput.selectedFiles.length > 0
            objectName: "startComparisonBtn"
            Accessible.name: "Iniciar comparación"
            activeFocusOnTab: true
            Keys.onReturnPressed: onClicked()
            Keys.onSpacePressed: onClicked()
            onClicked: {
                if (root.labService && root.labService.compareFiles)
                    root.labService.compareFiles(
                        refInput.selectedFiles[0],
                        targetInput.selectedFiles[0]
                    )
            }
        }
    }
}
