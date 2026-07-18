import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Disc Lab"
    objectName: "discLabPage"
    focus: true
    id: root

    property var disc: typeof discLabBridge !== "undefined" ? discLabBridge : null

    enum State { LOADING, READY, EMPTY, ERROR, UNAVAILABLE }
    property int pageState: root.disc ? DiscLabPage.READY : DiscLabPage.UNAVAILABLE
    property string errorMessage: ""
    property string ripFormat: "flac"
    property string ripDestination: "/home/user/Music/CD Rips"
    property bool canRip: root.disc && root.disc.status === "scanned" && ripFormat !== ""

    function refresh() {
        if (!root.disc) { root.pageState = DiscLabPage.UNAVAILABLE; return }
        root.pageState = DiscLabPage.LOADING
        try {
            root.disc.refresh()
            root.pageState = DiscLabPage.READY
        } catch (e) {
            root.pageState = DiscLabPage.ERROR
            root.errorMessage = String(e)
        }
    }

    Component.onCompleted: root.refresh()

    Item {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl

        LoadingState {
            anchors.fill: parent
            title: "Cargando Disc Lab..."
            visible: root.pageState === DiscLabPage.LOADING
        }

        ErrorState {
            anchors.fill: parent
            title: "Error"
            message: root.errorMessage
            showRetry: true
            onRetryRequested: root.refresh()
            visible: root.pageState === DiscLabPage.ERROR
        }

        UnavailableState {
            anchors.fill: parent
            title: "Disc Lab no disponible"
            message: "No se detectó unidad de disco o el servicio no está activo."
            visible: root.pageState === DiscLabPage.UNAVAILABLE
        }

        EmptyState {
            anchors.fill: parent
            title: "Sin disco"
            subtitle: "Inserta un disco o conecta una unidad externa."
            visible: root.pageState === DiscLabPage.EMPTY
        }

        Flickable {
            visible: root.pageState === DiscLabPage.READY
            id: flickable
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentHeight: column.height + MichiTheme.spacing.xxl

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Disc Lab"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                HeroMaterial {
                    width: parent.width; height: 140; radius: MichiTheme.radius.lg; showGlow: true
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                        Text { text: "Laboratorio de discos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Detección, análisis y ripping de CD/DVD."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    Text { text: "Unidad:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                    StatusBadge {
                        text: root.disc ? root.disc.status : "unavailable"
                        kind: root.disc && root.disc.status === "ready" ? "success" :
                              root.disc && root.disc.status === "scanning" ? "warning" :
                              root.disc && root.disc.status === "scanned" ? "success" : "disconnected"
                    }
                }

                Text {
                    text: root.disc ? root.disc.driveInfo : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton { text: "Detectar unidad"; variant: "primary"; onClicked: { if (root.disc) root.disc.refresh() } }
                    MichiButton { text: "Escanear disco"; variant: "secondary"; enabled: root.disc && root.disc.status === "ready"; onClicked: { if (root.disc) root.disc.scanDisc() } }
                }

                SectionHeader { text: "Pistas detectadas"; width: parent.width }

                Repeater {
                    model: root.disc ? root.disc.tracks : []

                    GlassMaterial {
                        width: parent.width; height: 36; radius: MichiTheme.radius.sm; variant: "base"
                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                            Text { width: 30; text: modelData.track || ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            Text { width: parent.width - 50; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }
                }

                Text {
                    text: root.disc && root.disc.tracks.length === 0 ? (root.disc && root.disc.status === "unavailable" ? "Servicio de discos no disponible." : "Escanea un disco para ver sus pistas.") : ""
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    ComboBox {
                        id: formatSelector
                        width: 120
                        model: ["flac", "wav", "mp3", "ogg"]
                        currentIndex: 0
                        onCurrentIndexChanged: {
                            ripFormat = model[currentIndex]
                            if (root.disc) root.disc.setFormat(ripFormat)
                        }
                    }

                    TextField {
                        id: destField
                        width: parent.width - formatSelector.width - browseBtn.width - MichiTheme.spacing.sm * 2
                        text: root.ripDestination
                        placeholderText: "Carpeta de destino"
                        onTextChanged: {
                            ripDestination = text
                            if (root.disc) root.disc.setDestination(ripDestination)
                        }
                    }

                    Button {
                        id: browseBtn
                        text: "..."
                        onClicked: {
                            // FolderDialog se abriría desde Qt Quick Dialogs
                        }
                    }
                }

                MichiButton {
                    Accessible.role: Accessible.Button
                    activeFocusOnTab: true
                    text: "Rip CD"
                    variant: "primary"
                    width: parent.width
                    enabled: root.canRip
                    onClicked: {
                        if (root.disc) {
                            root.disc.setFormat(ripFormat)
                            root.disc.setDestination(ripDestination)
                            root.disc.startExtraction()
                        }
                    }
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        StatusBadge { text: "Contractual — Sin unidad física no se declara verificado"; kind: "info" }
                        StatusBadge { text: "Experimental — Sin ripping automático"; kind: "experimental" }
                    }
                }
            }
        }
    }
}
