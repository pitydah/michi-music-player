import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root
    closePolicy: Popup.CloseOnEscape

    property var radioBridge: null
    property var stationData: null
    property int _stationId: root.stationData ? root.stationData.id || 0 : 0

    title: qsTr("Editar emisora")
    modal: true
    standardButtons: Dialog.Close
    width: Math.min(parent.width * 0.8, 450)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3

    padding: MichiTheme.spacing.lg

    onOpened: {
        nameField.text = root.stationData ? root.stationData.name || "" : ""
        urlField.text = root.stationData ? root.stationData.url || "" : ""
        codecField.text = root.stationData ? root.stationData.codec || "" : ""
        countryField.text = root.stationData ? root.stationData.country || "" : ""
    }

    Column {
        spacing: MichiTheme.spacing.md
        width: parent.width

        MichiSearchField { id: nameField; width: parent.width; placeholderText: qsTr("Nombre") }
        MichiSearchField { id: urlField; width: parent.width; placeholderText: qsTr("URL") }
        MichiSearchField { id: codecField; width: parent.width; placeholderText: qsTr("Codec") }
        MichiSearchField { id: countryField; width: parent.width; placeholderText: qsTr("País") }

        Row {
                Accessible.role: Accessible.Button

            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                text: qsTr("Cancelar")
                flat: true
                onClicked: root.close()
            }

            Button {
                text: qsTr("Guardar")
                enabled: nameField.text.trim() !== "" && urlField.text.trim() !== ""
                onClicked: {
                    if (root.radioBridge && typeof root.radioBridge.editStation === "function") {
                        root.radioBridge.editStation(
                            root._stationId,
                            nameField.text.trim(),
                            urlField.text.trim(),
                            codecField.text.trim(),
                            countryField.text.trim()
                        )
                        root.close()
                    }
                }
            }
        }
    }
}
