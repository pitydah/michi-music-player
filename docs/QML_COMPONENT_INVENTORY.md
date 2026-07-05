# QML Component Inventory

Fecha: 2026-07-05

Alcance: componentes, materiales, theme, shell y subcomponentes visuales bajo `ui_qml/`.

| Componente | Uso | Variantes | Duplicados | Accion |
|---|---|---|---|---|
| `MichiTheme.qml` | Entrada singleton de tokens | Colores, tipografia, spacing, motion, radios, opacidades | N/A | Mantener como contrato unico y ampliar con breakpoints, hit targets, icon sizes, density, focus, disabled y reduced motion. |
| `MichiColors.qml` | Paleta de identidad | Backgrounds, surfaces, text, badges, status | `Qt.rgba` repetido fuera del theme | Promover colores semanticos faltantes: hover, pressed, track bg, danger subtle, text on error, accent canonical. |
| `MichiSpacing.qml` | Espaciado base | xs, sm, md, lg, xl, xxl, page | Medidas directas 2, 3, 24, 28, 32, 40, 140 | Ampliar con `controlGap`, `listRow`, `toolbar`, `panel`, `pageCompact`. |
| `MichiTypography.qml` | Escala tipografica | hero, page, section, card, body, meta, badge | `captionSize` usado pero no definido; `FontWeight.*` mezclado | Agregar `captionSize`, `smallSize`, `tableSize`; exigir pesos via tokens. |
| `MichiMotion.qml` | Duraciones/easing | fast, normal, slow | Animaciones directas 150/1200 y sin reduced motion | Agregar `reducedMotion`, `duration(kind)` y token para indeterminate. |
| `GlassMaterial.qml` | Superficie smoked base | base, compact, elevated, accent, floating, status, hero, danger | `Rectangle` directos con surfaces similares | Mantener canonico; mover colores internos a `MichiColors`. |
| `HeroMaterial.qml` | Panel hero | glow/no glow | Heroes repetidos de 140 px | Crear `HeroPanel` canonico para paginas y responsive height. |
| `InputMaterial.qml` | Fondo de inputs | focused/hovered | `TextField` nativo sin estilo en paginas | Crear `MichiTextField` o adaptar `SearchField` para input general. |
| `PopupMaterial.qml` | Superficie de popup | radio/radius | Dialogs nativos y `CommandPalette` rectangle propio | Usarlo en palette, dialogs y context menus. |
| `SidebarMaterial.qml` | Fondo sidebar | Unico | N/A | Mantener, integrar collapsed/focus visuals. |
| `MichiButton.qml` | Boton texto | primary, secondary/ghost por fallback, danger | `Button` nativo en Lyrics, rectangulos clickeables | Canonico para texto; agregar icon slot, loading, destructive confirmation, accessible role/name. |
| `MichiIconButton.qml` | Boton icon-only | selected, disabled, tooltip, iconSource/iconText | Play/pause custom, glyph buttons, `[X]`, `<<`, `>>` | Canonico para icon-only; eliminar `iconText` como icono principal salvo contador breve. |
| `MichiSlider.qml` | Slider custom | value/from/to/step, keyboard arrows | `NowPlayingSeekBar`, `NowPlayingVolume` reimplementan track | Reutilizarlo o extraer `MichiTrackControl` para seek/volume/progress. |
| `MichiProgressBar.qml` | Progreso determinate/indeterminate | indeterminate infinite | Loading states en paginas usan texto plano | Usar para async feedback y respetar reduced motion. |
| `MichiBadge.qml` | Badge alternativo | info, success, warning, danger, experimental | `StatusBadge.qml` | Consolidar en `StatusBadge` o absorber diferencias. |
| `StatusBadge.qml` | Estado/etiqueta | info, success, warning, error, experimental, disconnected, active | `MichiBadge`, textos sueltos de estado | Mantener canonico; agregar accessible name y tooltip opcional. |
| `FilterChip.qml` | Filtros pequenos | selected/unselected | Filtros inline por pagina | Mantener, agregar focus/keyboard/Accessible.role CheckBox. |
| `SearchField.qml` | Busqueda | placeholder, submit/change | Usado como input generico en Radio | Separar `MichiSearchField` y `MichiTextField`. |
| `EmptyState.qml` | Empty state canonico | icon/title/subtitle/action | Empty states manuales en Library, Album, Artist, Metadata, Radio, Devices | Reutilizar en todas las paginas. |
| `GlassCard.qml` | Card interactiva generica | title/subtitle/variant | Cards especificas de home, album, device, connection | Mantener para cards simples; agregar focus y role Button. |
| `GlassPanel.qml` | Panel con header | title/subtitle/content | Muchos `GlassMaterial` con Column interna | Usar para secciones repetidas con header. |
| `PageHeader.qml` | Encabezado de pagina | title/subtitle/actions | Headers manuales en pages | Convertir en canonico para todas las paginas internas. |
| `SectionHeader.qml` | Titulo de seccion | text | Manual headers similares | Mantener y agregar action slot opcional. |
| `IconSlot.qml` | Placeholder iconografico | text icon | Duplicado con placeholders `AL`, `AR`, `BL`, `MI` | Reemplazar por icon asset/cover placeholder canonico. |
| `CoverImage.qml` | Portada generica | coverKey/radius | Album views usan rectangles con iniciales | Canonico para caratulas reales/placeholders. |
| `NowPlayingCover.qml` | Portada now playing | placeholderMode/coverKey | `CoverImage` overlap | Mantener si necesita estado de reproduccion; compartir placeholder style con `CoverImage`. |
| `NowPlayingBar.qml` | Barra global de reproduccion | compacto horizontal | `ExpandedNowPlayingPanel`, `PlaybackPage` replican controles | Mantener, pero extraer layout responsive y accessible controls. |
| `NowPlayingControls.qml` | Shuffle/prev/play/next/repeat | icon png, selected, supported | Play/pause custom en `ExpandedNowPlayingPanel` | Hacer canonico compartido por bar, page y expanded panel. |
| `NowPlayingSeekBar.qml` | Seek horizontal | position/duration/enabled | `MichiSlider` | Rehacer sobre control canonico focusable. |
| `NowPlayingVolume.qml` | Volumen/mute | volume/muted/supported | `MichiSlider` | Rehacer sobre control canonico, ampliar accessible role/value. |
| `ExpandedNowPlayingPanel.qml` | Panel expandido | expanded/collapsed | `PlaybackPage` y NowPlayingControls | Mantener como detalle ligero, no duplicar UX de PlaybackPage. |
| `NowPlayingQueuePanel.qml` | Queue compacta | expanded | Queue manual en `PlaybackPage` | Usarlo tambien en playback o extraer `QueueList`. |
| `SongContextMenu.qml` | Menu de canciones | acciones fijas | Context menus futuros | Convertir en `MichiContextMenu` con items, focus, escape, disabled. |
| `SongTable.qml` | Tabla de canciones | headers, list, context menu, empty | `PlaylistDetailPage` repite rows | Mantener como tabla canonica; agregar columnas min/max y seleccion. |
| `SongRow.qml` | Fila de cancion | hover/play/right click | Rows en playlist/queue/history | Canonico para track rows, con variants compact/table/queue. |
| `AlbumCard.qml` | Card de album | title/artist/track count | Album view delegates propios | Hacer base de album tile para todas las vistas. |
| `AlbumGrid.qml` | Grid album viejo | 200x260 cells | `AlbumGridView.qml` | Consolidar con `AlbumGridView` o deprecar uno. |
| `AlbumGridView.qml` | Vista album grid | 180x240 cells | `AlbumGrid.qml`, `AlbumCard.qml` | Reescribir sobre `AlbumCard`/`CoverImage`. |
| `AlbumCoverFlowView.qml` | Cover flow | PathView | N/A | Mantener como vista opcional; reduced motion y fallback. |
| `AlbumVinylWallView.qml` | Vinyl wall | circular placeholders | N/A | Usar portada real/placeholder canonico. |
| `AlbumTimelineView.qml` | Discografia cronologica | ListView sectioned | N/A | Refinar con row canonica. |
| `AlbumMagazineView.qml` | Lista editorial | alternating rows | N/A | Refinar o fusionar con timeline/list mode. |
| `AlbumViewSelector.qml` | Selector de vistas album | Tabs/chips | TabBar custom en Library | Usar patron segmentado canonico. |
| `ArtistCard.qml` | Card artista | cover/counts | AlbumCard parecido | Mantener, compartir `MediaCardBase`. |
| `ArtistList.qml` | Grid artistas | 190x220 cells | N/A | Responsive grid y empty canonico. |
| `MetadataFieldRow.qml` | Row de metadata | label/value | Form rows manuales en editor | Mantener y ampliar a editable. |
| `MetadataArtworkPreview.qml` | Preview artwork | status/cover | CoverImage | Mantener, usar panel/card canonico. |
| `CommandPalette.qml` | Overlay de comandos | fixed 400x320 | Popup/dialog patterns | Usar `PopupMaterial`, accessible modal, keyboard selection y responsive width. |
| `ConfirmActionDialog.qml` | Confirmacion | danger/non-danger | Dialog nativo en playlists | Convertir en dialog canonico para acciones destructivas. |
| `ToastHost.qml` | Notificaciones | success/warning/error/info | Mensajes inline dispersos | Mantener, mover colores a theme y reemplazar `[X]` por icon button. |
| `LyricsSearchDialog.qml` | Dialog de busqueda letra | TextField/Button nativos | Dialogs no canonicos | Aplicar `PopupMaterial`/`MichiButton`/`MichiTextField`. |
| `SyncedLyricsView.qml` | Lyrics sincronizada | active line/autoscroll | Usa token `accent` inexistente y Unicode | Reparar token, reduced motion y control accesible. |
| Home cards | Inicio | `HomeHero`, `ContinueCard`, `LibraryStatusCard`, `EcosystemCard`, `AssistantCard` | Algunos datos hardcoded/empty | Mantener, conectar datos reales y revisar responsive 1 columna. |
| Ecosystem cards | Connections/HomeAudio/Devices | server/device/receiver cards | Muchas cards parecidas | Extraer `DeviceStatusCard`/`ConnectionCardBase`. |
