"""Mario en marinière : rayures sur la chemise, dans toutes ses poses.

Les graphismes de Mario (GFX32, 4bpp) sont compressés en $08:8000 et
décompressés en RAM au démarrage. Casquette et chemise utilisent les mêmes
couleurs (indices 9 et 13 de sa palette). On regarde la feuille de tuiles
telle qu'elle s'affiche (16 tuiles par rangée, les poses y sont dessinées
entières) et, pour chaque zone de ces couleurs :
  - si elle touche la salopette (indices 10, 11, 12, au besoin à travers un
    pixel de contour : blocs du corps), ou si
    la peau (indice 6) est surtout au-dessus d'elle (torse sous le visage,
    dans les blocs de la tête), c'est la chemise : une rangée sur deux devient
    bleu marine (indice 10, l'ombre de la salopette) ;
  - si la peau est surtout en dessous, c'est la casquette : on n'y touche pas ;
  - les zones qui touchent les dorés de la cape (indices 4, 5) sont ignorées.
La palette (graphismes/palettes.txt) rend la chemise et la casquette blanches.
"""
import gfx
from smwrom import lz2_decompress

PC = 0x040000          # $08:8000
SHIRT = {9, 13}        # (14 est l'ombre de la peau, pas la chemise)
OUTLINE = {2, 3, 8}
SKIN = 6
OVERALLS = {10, 11, 12}
CAPE = {4, 5}          # dorés de la cape (le 3 est le contour de Mario)
STRIPE = 10
REACH = 7              # distance (pixels) où l'on cherche la peau
# tuiles 8x8 à ne jamais rayer : casquette vue de dos, doublure de cape,
# bord arrière de la casquette
EXCLUDE_TILES = {0x160, 0x161, 0x170, 0x171, 0x082, 0x083, 0x092, 0x093,
                 0x100, 0x101, 0x2AA, 0x2AB, 0x29A, 0x29B,
                 0x0A0, 0x0A1, 0x0B0, 0x0B1,
                 0x080, 0x081, 0x090, 0x091, 0x0A2, 0x0A3, 0x0B2, 0x0B3,
                 0x1E6, 0x1E7, 0x226, 0x227, 0x2A6, 0x2A7}
STRIPED = set()


def stripe(tiles):
    n = len(tiles)
    w, h = 128, ((n + 15) // 16) * 8

    def tid(x, y):
        return (y // 8) * 16 + x // 8

    def get(x, y):
        if not (0 <= x < w and 0 <= y < h) or tid(x, y) >= n:
            return 0
        return tiles[tid(x, y)][y % 8][x % 8]

    seen, changed = set(), 0
    for y0 in range(h):
        for x0 in range(w):
            if (x0, y0) in seen or get(x0, y0) not in SHIRT:
                continue
            comp, stack, cape, touches = [], [(x0, y0)], False, False
            seen.add((x0, y0))
            while stack:
                x, y = stack.pop(); comp.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    c = get(x + dx, y + dy)
                    if c in CAPE:
                        cape = True
                    elif c in OVERALLS or (c in OUTLINE and get(x + 2 * dx, y + 2 * dy) in OVERALLS):
                        touches = True          # directement ou à travers le contour
                    elif c in SHIRT and (x + dx, y + dy) not in seen:
                        seen.add((x + dx, y + dy)); stack.append((x + dx, y + dy))
            if cape:
                continue
            up = sum(1 for x, y in comp if any(get(x, y - k) == SKIN for k in range(1, REACH + 1)))
            down = sum(1 for x, y in comp if any(get(x, y + k) == SKIN for k in range(1, REACH + 1)))
            if touches or up > down:
                for x, y in comp:
                    if y % 2 == 0 and tid(x, y) not in EXCLUDE_TILES:
                        tiles[tid(x, y)][y % 8][x % 8] = STRIPE
                        STRIPED.add(tid(x, y)); changed += 1
    return changed


def apply(rom):
    raw = lz2_decompress(rom, PC)
    tiles = gfx.decode4(raw)
    n = stripe(tiles)
    data = gfx.encode4(tiles)
    comp = gfx.lz2_compress(data)
    assert lz2_decompress(comp, 0) == data
    old = gfx.compressed_size(rom, PC)
    if len(comp) > old:
        raise ValueError("GFX32 : %d octets, ne tient plus (%d)" % (len(comp), old))
    rom[PC:PC + old] = comp + b"\xFF" * (old - len(comp))
    return "Marinière : %d pixels rayés, GFX32 %d octets (place d'origine %d)" % (n, len(comp), old)
