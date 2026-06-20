#!/usr/bin/python3
"""Convert Recraft SVGs to clean transparent PNGs.

Renders SVG to high-res, removes edge-connected black background,
crops to content, centers on square canvas, exports at multiple sizes.
"""

import sys
from pathlib import Path
from collections import deque

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


SRC_SIDEBAR = Path("/home/cristian/Descargas/sidebar outpaint")
SRC_NOWPLAYING = Path("/home/cristian/Descargas/nowplayingbar outpaint")
PROJECT_ROOT = Path("/home/cristian/music_player")
DEST_SIDEBAR = PROJECT_ROOT / "icons/sidebar_clean"
DEST_NOWPLAYING = PROJECT_ROOT / "icons/nowplaying_clean"

SIDEBAR_MAP = [
    ("songs.svg", "sidebar_library"),
    ("songs.svg", "sidebar_songs"),
    ("album.svg", "sidebar_albums"),
    ("idenify.svg", "sidebar_identifier"),
    ("sidebar_unplayed.svg", "sidebar_unplayed"),
    ("sidebar_add.svg", "sidebar_add"),
    ("radio.svg", "sidebar_radio"),
    ("playlists.svg", "sidebar_playlists"),
    ("playlists.svg", "sidebar_playlist_item"),
    ("navidrome.svg", "sidebar_navidrome"),
    ("mix.svg", "sidebar_mix"),
    ("jellyfin.svg", "sidebar_jellyfin"),
    ("folders.svg", "sidebar_folders"),
    ("favorites.svg", "sidebar_popular"),
    ("connect-server.svg", "sidebar_servers"),
]

NOWPLAYING_MAP = [
    ("play.svg", "warm_play"),
    ("pause.svg", "warm_pause"),
    ("prev.svg", "warm_prev"),
    ("next.svg", "warm_next"),
    ("shuffle.svg", "warm_shuffle"),
    ("bucle.svg", "warm_repeat"),
    ("equalizer.svg", "warm_eq"),
    ("airplay.svg", "warm_transmit"),
    ("high.svg", "warm_vol_high"),
    ("mid.svg", "warm_vol_medium"),
    ("low.svg", "warm_vol_low"),
    ("mute.svg", "warm_mute"),
]


def render_svg_to_image(svg_path: str, size: int = 512) -> QImage:
    """Render SVG to QImage at given size."""
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return None

    vb = renderer.viewBoxF()
    if vb.isEmpty():
        vb = QRectF(0, 0, 24, 24)

    scale = size / max(vb.width(), vb.height())
    w = int(vb.width() * scale)
    h = int(vb.height() * scale)

    image = QImage(w, h, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    return image


def remove_edge_black_background(image: QImage) -> QImage:
    """Remove edge-connected dark pixels by flood fill."""
    w, h = image.width(), image.height()

    # Find all dark pixels connected to edges
    mask = [[False] * w for _ in range(h)]
    queue = deque()

    for y in range(h):
        for x in (0, w - 1):
            c = QColor.fromRgba(image.pixel(x, y))
            if c.alpha() > 10 and c.red() < 35 and c.green() < 35 and c.blue() < 35:
                mask[y][x] = True
                queue.append((x, y))
    for x in range(w):
        for y in (0, h - 1):
            c = QColor.fromRgba(image.pixel(x, y))
            if c.alpha() > 10 and c.red() < 35 and c.green() < 35 and c.blue() < 35 and not mask[y][x]:
                mask[y][x] = True
                queue.append((x, y))

    dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    while queue:
        x, y = queue.popleft()
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not mask[ny][nx]:
                c = QColor.fromRgba(image.pixel(nx, ny))
                if c.alpha() > 10 and c.red() < 35 and c.green() < 35 and c.blue() < 35:
                    mask[ny][nx] = True
                    queue.append((nx, ny))

    # Set edge-connected dark pixels to transparent
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                c = QColor.fromRgba(image.pixel(x, y))
                c.setAlpha(0)
                image.setPixel(x, y, c.rgba())

    return image


def find_content_bounds(image: QImage) -> tuple[int, int, int, int] | None:
    """Find bounding box of non-transparent pixels."""
    w, h = image.width(), image.height()
    min_x, min_y = w, h
    max_x, max_y = 0, 0

    for y in range(h):
        for x in range(w):
            c = QColor.fromRgba(image.pixel(x, y))
            if c.alpha() > 10:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if min_x > max_x or min_y > max_y:
        return None
    return (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def export_centered(image: QImage, size: int, padding: int) -> QImage:
    """Crop to content, center on square canvas."""
    bounds = find_content_bounds(image)
    if bounds is None:
        return None

    bx, by, bw, bh = bounds
    cropped = image.copy(bx, by, bw, bh)

    target = size - padding * 2
    scale = min(target / bw, target / bh)
    nw = int(bw * scale)
    nh = int(bh * scale)

    result = QImage(size, size, QImage.Format_ARGB32)
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    ox = (size - nw) // 2
    oy = (size - nh) // 2
    scaled = cropped.scaled(nw, nh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter.drawImage(ox, oy, scaled)
    painter.end()

    return result


def process_directory(src_dir: Path, dest_dir: Path, name_map: list,
                      sizes: list[int], padding: int = 4):
    """Process all SVGs in src_dir, export clean PNGs to dest_dir."""
    if not src_dir.exists():
        print(f"  SKIP: {src_dir} not found")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    svgs = {p.name: p for p in sorted(src_dir.glob("*.svg")) if p.is_file()}
    if not svgs:
        print(f"  No SVGs found in {src_dir}")
        return 0

    done = 0
    rendered = {}
    already = set()

    for src_name, out_name in name_map:
        if (src_name, out_name) in already:
            continue
        already.add((src_name, out_name))

        svg = svgs.get(src_name)
        if not svg:
            print(f"  SKIP {src_name}: file not found")
            continue

        if src_name not in rendered:
            img = render_svg_to_image(str(svg), 512)
            if img is None:
                print(f"  SKIP {src_name}: render failed")
                continue
            img = remove_edge_black_background(img)
            rendered[src_name] = img

        img = rendered[src_name]
        for sz in sizes:
            out_img = export_centered(img, sz, padding)
            if out_img:
                path = dest_dir / f"{out_name}_{sz}.png"
                out_img.save(str(path), "PNG")
                done += 1

    print(f"  {src_dir.name}: {len(rendered)} icons, {done} PNGs exported")
    return done


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    sidebar_sizes = [24, 64]
    nowplaying_sizes = [32, 64, 128]

    print("=== Sidebar icons ===")
    n1 = process_directory(SRC_SIDEBAR, DEST_SIDEBAR, SIDEBAR_MAP, sidebar_sizes, 2)

    print("\n=== NowPlaying icons ===")
    n2 = process_directory(SRC_NOWPLAYING, DEST_NOWPLAYING, NOWPLAYING_MAP, nowplaying_sizes, 4)

    print(f"\nTotal: {n1 + n2} PNGs exported")
    app.quit()


if __name__ == "__main__":
    main()
