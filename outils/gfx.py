"""Graphismes : décodage/encodage des tuiles 3bpp de SMW, compression LC_LZ2,
réinsertion dans la ROM, et dessins décrits en texte (dossier graphismes/).

Format d'un fichier graphismes/*.txt :
    fichier = 1E                 ; numéro du fichier GFX (hexa)
    tuiles = 0A 0B 1A 1B         ; tuiles 8x8 : haut-gauche haut-droite bas-gauche bas-droite
    (puis autant de lignes que de pixels, un caractère par pixel)
Caractères : '.' = transparent (couleur 0), '1'-'7' = couleurs 1 à 7 de la palette.
Pour 2 tuiles de large, 16 caractères par ligne ; 16 lignes pour 2 de haut.
"""
from smwrom import snes_to_pc, pc_to_snes, lz2_decompress

PTR_LO, PTR_HI, PTR_BK = snes_to_pc(0x00B992), snes_to_pc(0x00B9C4), snes_to_pc(0x00B9F6)

# Espace libre (rempli de $FF dans la ROM d'origine) où placer un fichier GFX
# recompressé qui ne tiendrait plus à sa place.
FREE_GFX = [(0x0EF0F0, 0x0F0000 - 0x0EF0F0 - 0x10)]


# --- tuiles 3bpp ---------------------------------------------------------------
def decode3(data):
    tiles = []
    for t in range(len(data) // 24):
        b = t * 24
        tiles.append([[((data[b + y * 2] >> (7 - x)) & 1) | (((data[b + y * 2 + 1] >> (7 - x)) & 1) << 1) |
                       (((data[b + 16 + y] >> (7 - x)) & 1) << 2) for x in range(8)] for y in range(8)])
    return tiles


def encode3(tiles):
    out = bytearray()
    for tile in tiles:
        p01, p2 = bytearray(16), bytearray(8)
        for y in range(8):
            for x in range(8):
                c, bit = tile[y][x], 1 << (7 - x)
                if c & 1: p01[y * 2] |= bit
                if c & 2: p01[y * 2 + 1] |= bit
                if c & 4: p2[y] |= bit
        out += p01 + p2
    return bytes(out)


# --- compression LC_LZ2 -------------------------------------------------------
def _header(cmd, n):
    n -= 1
    if n < 32:
        return bytes([(cmd << 5) | n])
    return bytes([0xE0 | (cmd << 2) | (n >> 8), n & 0xFF])


def lz2_compress(data):
    data = bytes(data)
    n = len(data)
    out = bytearray()
    lit = bytearray()

    def flush():
        i = 0
        while i < len(lit):
            chunk = lit[i:i + 1024]
            out.extend(_header(0, len(chunk)) + chunk)
            i += len(chunk)
        lit.clear()

    i = 0
    while i < n:
        best = (0, None, None)   # (gain, cmd, info)
        # 1 : même octet répété
        j = i
        while j < n and j - i < 1024 and data[j] == data[i]:
            j += 1
        if j - i >= 3:
            best = max(best, (j - i - 2, 1, j - i), key=lambda b: b[0])
        # 2 : deux octets alternés
        if i + 1 < n:
            j = i
            while j < n and j - i < 1024 and data[j] == data[i + ((j - i) & 1)]:
                j += 1
            if j - i >= 4:
                best = max(best, (j - i - 3, 2, j - i), key=lambda b: b[0])
        # 3 : suite croissante
        j = i
        while j < n and j - i < 1024 and data[j] == (data[i] + (j - i)) & 0xFF:
            j += 1
        if j - i >= 3:
            best = max(best, (j - i - 2, 3, j - i), key=lambda b: b[0])
        # 4 : copie d'un passage déjà écrit (adresse absolue)
        bl, bp = 0, 0
        start = 0
        first = data[i]
        p = data.find(bytes([first]), start, i)
        while p != -1:
            L = 0
            while i + L < n and L < 1024 and data[p + L] == data[i + L]:
                L += 1
            if L > bl:
                bl, bp = L, p
            p = data.find(bytes([first]), p + 1, i)
        if bl >= 4:
            best = max(best, (bl - 3, 4, (bp, bl)), key=lambda b: b[0])
        gain, cmd, info = best
        if cmd is None or gain <= 0:
            lit.append(data[i]); i += 1
            continue
        flush()
        if cmd == 1:
            out += _header(1, info) + bytes([data[i]]); i += info
        elif cmd == 2:
            out += _header(2, info) + data[i:i + 2]; i += info
        elif cmd == 3:
            out += _header(3, info) + bytes([data[i]]); i += info
        else:
            p, L = info
            out += _header(4, L) + bytes([p >> 8, p & 0xFF]); i += L
    flush()
    out.append(0xFF)
    return bytes(out)


# --- accès aux fichiers GFX dans la ROM ----------------------------------------
def gfx_pc(rom, num):
    a = (rom[PTR_BK + num] << 16) | (rom[PTR_HI + num] << 8) | rom[PTR_LO + num]
    return snes_to_pc(a)


def compressed_size(rom, pc):
    """Taille d'un bloc LZ2 (en le parcourant)."""
    start = pc
    while True:
        h = rom[pc]; pc += 1
        if h == 0xFF:
            return pc - start
        cmd = h >> 5
        if cmd == 7:
            cmd = (h >> 2) & 7
            n = (((h & 3) << 8) | rom[pc]) + 1; pc += 1
        else:
            n = (h & 0x1F) + 1
        pc += {0: n, 1: 1, 2: 2, 3: 1, 4: 2}[cmd]


def read_gfx(rom, num):
    return decode3(lz2_decompress(rom, gfx_pc(rom, num)))


def write_gfx(rom, num, tiles, free=None):
    """Recompresse et réinsère un fichier GFX. Renvoie un texte de compte rendu."""
    data = encode3(tiles)
    comp = lz2_compress(data)
    assert lz2_decompress(comp, 0) == data, "erreur du compresseur LZ2"
    pc = gfx_pc(rom, num)
    old = compressed_size(rom, pc)
    if len(comp) <= old:
        rom[pc:pc + old] = comp + b"\xFF" * (old - len(comp))
        return "GFX%02X : %d octets (place d'origine %d)" % (num, len(comp), old)
    free = FREE_GFX if free is None else free
    for k, (addr, size) in enumerate(free):
        if size >= len(comp):
            p = snes_to_pc(addr)
            assert all(b == 0xFF for b in rom[p:p + len(comp)]), "espace libre déjà utilisé"
            rom[p:p + len(comp)] = comp
            rom[pc:pc + old] = b"\xFF" * old
            rom[PTR_LO + num] = addr & 0xFF
            rom[PTR_HI + num] = (addr >> 8) & 0xFF
            rom[PTR_BK + num] = addr >> 16
            free[k] = (addr + len(comp), size - len(comp))
            return "GFX%02X : %d octets, déplacé en $%06X (ne tenait plus dans %d)" % (num, len(comp), addr, old)
    raise ValueError("GFX%02X : plus de place (%d octets)" % (num, len(comp)))


# --- dessins texte ---------------------------------------------------------------
def parse_drawing(path):
    meta, rows = {}, []
    for line in open(path, encoding="utf-8"):
        line = line.split(";", 1)[0].rstrip()
        if not line.strip():
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            meta[k.strip()] = v.strip()
        else:
            rows.append(line.strip())
    num = int(meta["fichier"], 16)
    tiles = [int(t, 16) for t in meta["tuiles"].split()]
    w = 2 if len(tiles) >= 2 else 1
    h = (len(tiles) + w - 1) // w
    if len(rows) != h * 8 or any(len(r) != w * 8 for r in rows):
        raise ValueError("%s : il faut %d lignes de %d caractères" % (path, h * 8, w * 8))
    pix = [[0 if c == "." else int(c) for c in r] for r in rows]
    for r in pix:
        if any(c > 7 for c in r):
            raise ValueError("%s : couleurs 0 à 7 seulement" % path)
    return num, tiles, w, pix


def apply_drawing(all_tiles, tiles, w, pix):
    for k, t in enumerate(tiles):
        ox, oy = (k % w) * 8, (k // w) * 8
        all_tiles[t] = [[pix[oy + y][ox + x] for x in range(8)] for y in range(8)]


# --- tuiles 4bpp (graphismes de Mario, GFX32) ------------------------------------
def decode4(data):
    tiles = []
    for t in range(len(data) // 32):
        b = t * 32
        tiles.append([[((data[b + y * 2] >> (7 - x)) & 1) | (((data[b + y * 2 + 1] >> (7 - x)) & 1) << 1) |
                       (((data[b + 16 + y * 2] >> (7 - x)) & 1) << 2) |
                       (((data[b + 17 + y * 2] >> (7 - x)) & 1) << 3) for x in range(8)] for y in range(8)])
    return tiles


def encode4(tiles):
    out = bytearray()
    for tile in tiles:
        p = bytearray(32)
        for y in range(8):
            for x in range(8):
                c, bit = tile[y][x], 1 << (7 - x)
                if c & 1: p[y * 2] |= bit
                if c & 2: p[y * 2 + 1] |= bit
                if c & 4: p[16 + y * 2] |= bit
                if c & 8: p[17 + y * 2] |= bit
        out += p
    return bytes(out)
