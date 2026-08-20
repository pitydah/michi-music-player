import QtQuick
import "../patterns"

PageHeader {
    title: "Library"
    subtitle: library.fileCount > 0
        ? library.fileCount + " tracks · " + library.albumCount + " albums · "
            + library.artistCount + " artists"
        : "Your local music collection"
}
