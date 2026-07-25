import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "aiModelSelector"

    property string selectedModelId: "calico"
    property var selectedModel: modelAt(indexForId(selectedModelId))
    property bool integrationReady: false

    signal modelSelectionRequested(string modelId)

    implicitHeight: selectorColumn.implicitHeight
    Accessible.role: Accessible.Grouping
    Accessible.name: qsTr("Selector de modelos de Michi AI")
    Accessible.description: qsTr("Elige la personalidad visual que se conectará al motor de inteligencia artificial.")

    ListModel {
        id: aiModels

        ListElement {
            modelId: "calico"
            modelName: "Michi Calico"
            modelRole: "Versátil"
            modelDescription: "Equilibrado, cercano y preparado para acompañarte en toda la biblioteca."
            modelImage: "../../assets/ai_models/michi-calico.png"
        }
        ListElement {
            modelId: "munchkin"
            modelName: "Michi Munchkin"
            modelRole: "Ágil"
            modelDescription: "Directo y ligero para consultas rápidas y acciones cotidianas."
            modelImage: "../../assets/ai_models/michi-munchkin.png"
        }
        ListElement {
            modelId: "carey"
            modelName: "Michi Carey"
            modelRole: "Curador"
            modelDescription: "Especialista en descubrir conexiones, ambientes y nuevas escuchas."
            modelImage: "../../assets/ai_models/michi-carey.png"
        }
        ListElement {
            modelId: "maine_coon"
            modelName: "Michi Maine Coon"
            modelRole: "Experto"
            modelDescription: "Una presencia profunda para análisis musicales más exigentes."
            modelImage: "../../assets/ai_models/michi-maine-coon.png"
        }
        ListElement {
            modelId: "sphynx"
            modelName: "Michi Sphynx"
            modelRole: "Técnico"
            modelDescription: "Preciso y analítico, pensado para Audio Lab y tareas avanzadas."
            modelImage: "../../assets/ai_models/michi-sphynx.png"
        }
    }

    function indexForId(modelId) {
        for (var i = 0; i < aiModels.count; i++) {
            if (aiModels.get(i).modelId === modelId)
                return i
        }
        return 0
    }

    function modelAt(index) {
        if (index < 0 || index >= aiModels.count)
            return aiModels.get(0)
        return aiModels.get(index)
    }

    function selectModel(modelId) {
        if (indexForId(modelId) < 0)
            return
        selectedModelId = modelId
        modelSelectionRequested(modelId)
    }

    Column {
        id: selectorColumn
        width: parent.width
        spacing: MichiTheme.spacing.md

        RowLayout {
            width: parent.width
            spacing: MichiTheme.spacing.md

            Column {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Text {
                    text: qsTr("Elige tu Michi")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: qsTr("Cada modelo tendrá una especialidad. La conexión al motor de IA se añadirá más adelante.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
            }

            StatusBadge {
                text: root.integrationReady ? qsTr("Conectado") : qsTr("Vista previa")
                kind: root.integrationReady ? "success" : "experimental"
                Layout.alignment: Qt.AlignTop
            }
        }

        Rectangle {
            width: parent.width
            implicitHeight: 224
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceHero
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
            clip: true

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: MichiTheme.colors.accentSoft }
                    GradientStop { position: 0.52; color: MichiTheme.colors.surfaceSubtle }
                    GradientStop { position: 1.0; color: MichiTheme.colors.surfaceHero }
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                spacing: MichiTheme.spacing.xl

                Item {
                    Layout.preferredWidth: 168
                    Layout.fillHeight: true

                    Rectangle {
                        anchors.centerIn: parent
                        width: 154
                        height: 154
                        radius: width / 2
                        color: MichiTheme.colors.surfaceCardElevated
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderActive

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.xs
                            radius: width / 2
                            color: MichiTheme.colors.surfaceCard
                            clip: true

                            Image {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.sm
                                source: root.selectedModel ? root.selectedModel.modelImage : ""
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                mipmap: true
                                sourceSize.width: 320
                                sourceSize.height: 320
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: MichiTheme.spacing.sm

                    StatusBadge {
                        text: root.selectedModel ? root.selectedModel.modelRole : ""
                        kind: "active"
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.selectedModel ? root.selectedModel.modelName : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 680
                        text: root.selectedModel ? root.selectedModel.modelDescription : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Identidad seleccionada · Integración pendiente")
                        color: MichiTheme.colors.textTertiary
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
            }
        }

        Flickable {
            id: modelRail
            objectName: "aiModelRail"
            width: parent.width
            height: 112
            contentWidth: modelRow.width
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.HorizontalFlick
            ScrollBar.horizontal: ScrollBar {
                policy: modelRail.contentWidth > modelRail.width
                        ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            }

            Row {
                id: modelRow
                spacing: MichiTheme.spacing.sm

                Repeater {
                    model: aiModels

                    delegate: MichiCard {
                        required property string modelId
                        required property string modelName
                        required property string modelRole
                        required property string modelImage

                        controlObjectName: "aiModelCard_" + modelId
                        width: 196
                        height: 96
                        interactive: true
                        selected: root.selectedModelId === modelId
                        variant: "glass"
                        accessibleName: qsTr("Seleccionar %1").arg(modelName)
                        accessibleDescription: qsTr("%1, especialidad %2").arg(modelName).arg(modelRole)
                        onClicked: root.selectModel(modelId)

                        RowLayout {
                            width: parent.width
                            spacing: MichiTheme.spacing.md

                            Rectangle {
                                Layout.preferredWidth: 58
                                Layout.preferredHeight: 58
                                radius: width / 2
                                color: MichiTheme.colors.surfaceCardElevated
                                border.width: MichiTheme.borderWidth
                                border.color: root.selectedModelId === modelId
                                              ? MichiTheme.colors.borderActive
                                              : MichiTheme.colors.borderCard
                                clip: true

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: MichiTheme.spacing.xs
                                    source: modelImage
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    mipmap: true
                                    sourceSize.width: 128
                                    sourceSize.height: 128
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    Layout.fillWidth: true
                                    text: modelName.replace("Michi ", "")
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelRole
                                    color: root.selectedModelId === modelId
                                           ? MichiTheme.colors.accent
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
