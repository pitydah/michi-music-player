import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    id: root

    property real balance: 0.0
    property var audioBridge: null

    signal balanceSliderChanged(real value)

    objectName: "balanceSlider"

    Accessible.role: Accessible.Slider
    Accessible.name: "Balance"
    Accessible.description: "Ajusta el balance entre canal izquierdo y derecho"

    implicitWidth: 200
    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        spacing: MichiTheme.spacing.sm

        Text {
            text: "L"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            font.weight: MichiTheme.typography.weightMedium
            Accessible.name: "Canal izquierdo"
        }

        Slider {
            id: balanceSlider
            Layout.fillWidth: true
            from: -1.0
            to: 1.0
            value: root.balance
            stepSize: 0.05
            objectName: "balanceSliderValue"
            Accessible.name: "Balance"
            Accessible.description: "Valor: " + value.toFixed(2)

            onMoved: {
                root.balance = value
                if (root.audioBridge && typeof root.audioBridge.setBalance !== "undefined")
                    root.audioBridge.setBalance(value)
                root.balanceSliderChanged(value)
            }
        }

        Text {
            text: "R"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            font.weight: MichiTheme.typography.weightMedium
            Accessible.name: "Canal derecho"
        }
    }
}
