# Canonical NowPlayingBar golden

The project-supplied `tests/golden/now_playing_bar_reference.png` is the
authoritative geometry reference for M9.15. Its SHA-256 is
`fd731e61c87c772bbffd806b254a72c5d14f46c2b5141084fffcae54066e0dc5`.

At the canonical 1920×154 canvas, the implementation pins these measured
landmarks:

| Landmark | x | y | width | height |
| --- | ---: | ---: | ---: | ---: |
| Track card | 38 | 34 | 270 | 86 |
| Artwork inside track card | 12 | 12 | 64 | 64 |
| Timeline | 385 | 33 | 1162 | 28 |
| Central Play/Pause | 889 | 73 | 55 | 54 |
| Queue utility | 1560 | 82 | 36 | 36 |
| Volume slider | 1680 | 33 | 80 | 28 |
| Output badge | 1722 | 86 | 150 | 34 |

`tests/test_m9_now_playing_golden.py` pins the supplied screenshot byte for
byte. `tests/test_m9_qml.py` instantiates the production QML and verifies these
landmarks at the canonical canvas. The timeline is the only horizontally
elastic region at narrower desktop widths; control order and distribution do
not change.
