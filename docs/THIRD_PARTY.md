# Third-party software, services, inspirations, and legal declarations

Michi Music Player is an independent free-software music player for Linux/KDE.

This document consolidates third-party dependencies, optional integrations,
open-source inspirations, metadata tools, trademark notices, and file-level
attribution rules.

This document is informational. It does not replace the `LICENSE` file,
third-party license texts, or file-level notices.

## Project license

Michi Music Player is distributed under the GNU General Public License,
version 3 or later, unless a specific file states otherwise.

Recommended SPDX header for new source files:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Cristian Rosas
```

If any file has a different origin or license, that file must include its
own file-level notice.

## Direct dependencies

The following projects may be used as runtime or development dependencies.

| Project                       | Role in Michi                                    | Declaration                                 |
| ----------------------------- | ------------------------------------------------ | ------------------------------------------- |
| Python                        | Main programming language                        | Runtime dependency                          |
| PySide6 / Qt                  | Graphical user interface                         | Dependency; Qt/PySide licensing terms apply |
| GStreamer                     | Audio playback, decoding, media discovery        | Runtime dependency                          |
| SQLite                        | Local database, library, playlists, history, FTS | Runtime dependency                          |
| Mutagen                       | Reading/writing audio metadata                   | Direct Python dependency when used          |
| NumPy                         | Signal/audio-related processing                  | Python dependency                           |
| dbus-python                   | MPRIS desktop integration                        | Optional dependency                         |
| PyAudio / PortAudio           | Audio capture                                    | Optional dependency                         |
| fpcalc / Chromaprint          | Acoustic fingerprinting                          | Optional external tool                      |
| Avahi                         | mDNS discovery/publication                       | Optional system dependency                  |
| pactl / PulseAudio / PipeWire | Audio routing and null-sink workflows            | Optional system dependency                  |
| Snapcast                      | Multiroom audio target                           | Optional external runtime                   |

If binaries, Flatpaks, AppImages, packages, or bundled releases
redistribute third-party code, the corresponding license texts and notices
must be included.

## Open-source metadata, tagging, and library-management inspirations

Michi Music Player includes metadata, tagging, library organization,
filename parsing, album grouping, cover-art handling, and
music-identification workflows. Some of these ideas were conceptually
informed by existing open-source music metadata tools.

Unless a specific source file says otherwise, these projects are listed as
conceptual, workflow, or user-experience references only. Michi Music
Player does not intentionally include source code, UI assets, icons,
logos, screenshots, databases, or proprietary materials from these
projects.

| Project                 | Area of inspiration                                                                                                                    | Declaration                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| MusicBrainz Picard      | Acoustic fingerprinting, metadata lookup, release/recording matching, tag completion, album clustering, file renaming                  | Conceptual and workflow inspiration only                                     |
| beets                   | Command-line library management, importer workflow, metadata matching, file organization, plugin-oriented architecture, path templates | Conceptual and workflow inspiration only                                     |
| Kid3                    | Multi-format tag editing, batch tag editing, tag-from-filename and filename-from-tag workflows, cover-art handling                     | Conceptual UI/workflow inspiration only                                      |
| puddletag               | Spreadsheet-like batch metadata editing, bulk tag operations, tag field visibility, mass editing workflow                              | Conceptual UI/workflow inspiration only                                      |
| EasyTAG                 | Folder-based tag editing, recursive editing, filename masks, playlist generation, bulk field editing                                   | Conceptual workflow inspiration only                                         |
| Quod Libet / Ex Falso   | Flexible library organization, tag-driven browsing, advanced tag editing, user-defined organization logic                              | Conceptual workflow inspiration only                                         |
| Clementine              | Desktop music library organization, playlist handling, server/radio integration concepts                                               | Conceptual inspiration only                                                  |
| Strawberry Music Player | Modern Qt music player patterns, collection organization, metadata editing, cover-art workflows                                        | Conceptual inspiration only                                                  |
| MusicBrainz database    | Artist, release, recording, release group, and MusicBrainz ID concepts                                                                 | External metadata source; separate data licenses and attribution rules apply |
| AcoustID / Chromaprint  | Acoustic fingerprinting and matching workflows                                                                                         | Optional external service/tool concepts                                      |
| Mutagen                 | Audio metadata reading and writing                                                                                                     | Direct dependency when imported by Michi                                     |

General workflows such as reading tags, writing tags, parsing filenames,
renaming files from tags, organizing files into folders, matching tracks
to albums, using acoustic fingerprints, editing batches of tracks, and
exporting playlists are common software patterns. They must not be
described as copied from a specific application unless code was actually
copied or adapted.

## Music-library, playback, and UX inspirations

Michi Music Player is independently implemented, but some user-experience
ideas are conceptually informed by common patterns from existing music
software.

| Reference                          | Area of inspiration                                                           | Declaration                                                           |
| ---------------------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| iTunes / iPod-era music management | Library-as-master model, device sync workflow, local music management         | Conceptual UX inspiration only                                        |
| Apple Music / Music.app            | General library navigation and playback layout patterns                       | Conceptual UX inspiration only                                        |
| Cover Flow-style browsing          | Visual album carousel concept                                                 | Independently implemented visual concept; no Apple assets or branding |
| Roon                              | Rich library browsing, credits, high-detail metadata, audiophile organization | Conceptual inspiration only                                           |
| TIDAL                             | Credits, editorial metadata, premium music presentation                       | Conceptual inspiration only                                           |
| Spotify                           | Mixes, discovery, playlist-oriented listening                                 | Conceptual inspiration only                                           |
| Deezer Flow                       | Flow/mood listening concepts                                                  | Conceptual inspiration only                                           |
| Every Noise at Once               | Genre exploration and music-map concepts                                      | Conceptual inspiration only; no copied dataset or visualization       |
| Audirvana                         | Audiophile output profiles, DAC awareness, bit-perfect concepts               | Conceptual inspiration only                                           |

Do not use third-party logos, screenshots, icons, proprietary names as
feature names, trade dress, or copied visual assets.

## Local synchronization inspirations

Michi Sync is Michi Music Player's own synchronization concept for local
libraries, Android devices, LAN discovery, and transfer workflows.

| Reference                     | Area of inspiration                     | Declaration                                                                     |
| ----------------------------- | --------------------------------------- | ------------------------------------------------------------------------------- |
| LocalSend                     | Local-network discovery and transfer UX | Conceptual inspiration only; no LocalSend code or assets intentionally included |
| iPod/iTunes-style device sync | Library-master/device-client workflow   | Conceptual historical workflow reference only                                   |

Michi Sync should be described as Michi's own protocol and implementation
unless code is explicitly derived from another project.

## Integration and compatibility targets

Michi Music Player may interoperate with these systems when configured by
the user.

| System                       | Type of relationship                 | Declaration                                    |
| ---------------------------- | ------------------------------------ | ---------------------------------------------- |
| Home Assistant               | REST/media_player integration target | Unofficial integration; no endorsement implied |
| Snapcast                     | Optional multiroom audio runtime     | External optional software                     |
| Navidrome                    | Subsonic-compatible server target    | Compatibility target                           |
| Jellyfin                     | Media server target                  | Compatibility may be partial or API-dependent  |
| Subsonic-compatible servers  | Music streaming API target           | Protocol/API compatibility only                |
| Internet radio / ICY streams | Playback source                      | Stream rights remain with stream providers     |
| KDE Plasma                   | Desktop environment target           | No KDE endorsement implied                     |
| MPRIS                        | Desktop media control specification  | Interoperability target                        |

Compatibility does not mean certification, endorsement, partnership, or
complete feature parity.

## Metadata, recognition, lyrics, and external data providers

Michi may optionally use external metadata, lyrics, or recognition
services.

| Provider / tool             | Purpose                              | Declaration                                               |
| --------------------------- | ------------------------------------ | --------------------------------------------------------- |
| MusicBrainz                 | Music metadata and identifiers       | External data/service source; terms and attribution apply |
| AcoustID                    | Acoustic fingerprint matching        | Optional external service                                 |
| Chromaprint / fpcalc        | Fingerprint generation               | Optional external tool                                    |
| AudD                        | Music recognition API                | Optional external service                                 |
| Shazam-compatible libraries | Recognition provider                 | No Apple/Shazam affiliation implied                       |
| Wikipedia / Wikimedia       | Artist/album text or contextual data | Content license and attribution rules apply               |
| LRCLIB                      | Lyrics lookup                        | External lyrics provider; terms apply                     |

External metadata may be subject to copyright, database rights, API terms,
rate limits, and attribution requirements.

## Miro / Democracy Player

Historical project notes mention Miro Player / Democracy Player.

If any Michi source file contains code actually copied or adapted from
Miro, that file must retain a file-level notice identifying the original
source and license.

If no Miro code is present in a file, Miro should be listed only as
historical or conceptual inspiration.

## Trademarks and no endorsement

All third-party names, marks, logos, and product names are the property of
their respective owners.

Their mention in this repository is descriptive and nominative only.

Michi Music Player is not affiliated with, endorsed by, sponsored by, or
approved by Apple, Spotify, TIDAL, Deezer, Roon Labs, Audirvana,
LocalSend, Home Assistant, Snapcast, Navidrome, Jellyfin, Subsonic,
MusicBrainz, MetaBrainz, AcoustID, Chromaprint, AudD, Shazam, LRCLIB,
Wikipedia, Wikimedia, KDE, Qt, GStreamer, MusicBrainz Picard, beets,
Kid3, puddletag, EasyTAG, Quod Libet, Ex Falso, Clementine, Strawberry
Music Player, or Mutagen.

## No proprietary assets

Do not include third-party:

- logos;
- screenshots;
- icons;
- artwork;
- fonts;
- UI assets;
- sound files;
- copied documentation;
- proprietary algorithms;
- private APIs;
- proprietary protocol dumps;
- confidential reverse-engineered material;
- datasets or databases;

unless their license explicitly permits redistribution and the required
notices are included.

## File-level notice requirement

If any file is copied, translated, ported, adapted, or substantially
derived from another project, the file must include:

- original project name;
- original copyright holder;
- original license;
- source URL or commit when available;
- description of modifications;
- license compatibility note.

Without such a notice, mentions of third-party projects must be treated
only as conceptual references, dependencies, integration targets, or
compatibility targets.

## Packaging note

Linux packages, Flatpak manifests, AppImage builds, binary releases, and
source archives should include:

- `LICENSE`;
- `NOTICE`;
- `docs/THIRD_PARTY.md`;
- license texts for bundled third-party code;
- source code or written source-offer information required by the GPL when
  distributing binaries.
