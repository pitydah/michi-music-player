"""Library importer — adds ripped tracks to the music library.

File copy and library registration not yet implemented.
"""

from __future__ import annotations


class LibraryImporter:
    def build_destination_path(self, metadata: dict, profile: str) -> str:
        return ""

    def import_tracks(self, track_files: list[str], metadata: dict,
                      destination: str):
        pass

    def add_to_library(self, imported_files: list[str]):
        pass

    def refresh_library_index(self):
        pass
