"""Fonctions utilitaires pour lire/écrire une ROM Super Mario World (US, LoROM, sans header)."""

CLEAN_SHA1 = "6b47bb75d16514b6a476aa0c73a683a2a4c18765"


def snes_to_pc(addr):
    """Convertit une adresse SNES LoROM ($BB:AAAA) en offset fichier."""
    bank, low = addr >> 16, addr & 0xFFFF
    assert low >= 0x8000, hex(addr)
    return ((bank & 0x7F) << 15) | (low & 0x7FFF)


def pc_to_snes(pc):
    return ((pc >> 15) << 16) | 0x8000 | (pc & 0x7FFF)


def lz2_decompress(rom, pc):
    """Décompresse un bloc au format LC_LZ2 (utilisé pour les graphismes de SMW)."""
    out = bytearray()
    while True:
        h = rom[pc]; pc += 1
        if h == 0xFF:
            return bytes(out)
        cmd = h >> 5
        if cmd == 7:
            cmd = (h >> 2) & 7
            n = (((h & 3) << 8) | rom[pc]) + 1; pc += 1
        else:
            n = (h & 0x1F) + 1
        if cmd == 0:
            out += rom[pc:pc + n]; pc += n
        elif cmd == 1:
            out += bytes([rom[pc]]) * n; pc += 1
        elif cmd == 2:
            a, b = rom[pc], rom[pc + 1]; pc += 2
            for i in range(n):
                out.append(a if i % 2 == 0 else b)
        elif cmd == 3:
            v = rom[pc]; pc += 1
            for i in range(n):
                out.append((v + i) & 0xFF)
        elif cmd == 4:
            src = (rom[pc] << 8) | rom[pc + 1]; pc += 2  # big endian dans LZ2
            for i in range(n):
                out.append(out[src + i])
        else:
            raise ValueError("commande LZ2 inconnue %d" % cmd)


def gfx_file_pc(rom, num):
    """Offset fichier du fichier graphique GFX<num> (00-31)."""
    lo = rom[snes_to_pc(0x00B992) + num]
    hi = rom[snes_to_pc(0x00B9C4) + num]
    bk = rom[snes_to_pc(0x00B9F6) + num]
    return snes_to_pc((bk << 16) | (hi << 8) | lo)


# --- Texte (police layer 3, GFX2A) -------------------------------------------
# Pas de chiffres 8/9 dans la police d'origine ; les accents sont ajoutés.
CHARSET = {" ": 0x1F, "!": 0x1A, ".": 0x1B, "-": 0x1C, ",": 0x1D, "?": 0x1E,
           "#": 0x5A, "(": 0x5B, ")": 0x5C, "'": 0x5D}
for _i in range(26):
    CHARSET[chr(65 + _i)] = _i
    CHARSET[chr(97 + _i)] = 0x40 + _i
for _i, _c in enumerate("1234567"):
    CHARSET[_c] = 0x64 + _i
CHARSET["0"] = 0x6B
# Lettres accentuées ajoutées dans GFX2A (graphismes/police_accents.txt), à la
# place des tuiles « ILLUSION » et « YELLOW » des anciens noms de niveaux.
ACCENTED = "éèêàçùîôÉÂÎ"
for _i, _c in enumerate(ACCENTED):
    CHARSET[_c] = 0x32 + _i
DECODE = {v: k for k, v in CHARSET.items()}

ACCENTS = str.maketrans("àâäéèêëîïôöùûüçœÀÂÄÉÈÊËÎÏÔÖÙÛÜÇŒñÑ’",
                        "aaaeeeeiioouuucoAAAEEEEIIOOUUUCOnN'")


def normalize(s):
    """Remplace les lettres accentuées absentes de la police par la lettre simple."""
    return "".join(c if c in CHARSET else c.translate(ACCENTS) for c in s).replace("œ", "oe")


def encode_text(s, where=""):
    """Encode une chaîne en tuiles. Accepte {XX} pour une tuile brute (hexa)."""
    s = normalize(s)
    out, i = [], 0
    while i < len(s):
        if s[i] == "{":
            j = s.index("}", i)
            out.append(int(s[i + 1:j], 16)); i = j + 1
            continue
        c = s[i]
        if c not in CHARSET:
            raise ValueError("%s: caractère impossible dans la police SMW : %r (dans %r)" % (where, c, s))
        out.append(CHARSET[c]); i += 1
    return out


def decode_text(tiles):
    return "".join(DECODE.get(t & 0x7F, "{%02X}" % (t & 0x7F)) for t in tiles)


def text_len(s):
    return len(encode_text(s))


def fix_checksum(rom):
    """Recalcule la somme de contrôle interne (ROM 512 Ko / LoROM)."""
    rom[0x7FDC:0x7FE0] = b"\xFF\xFF\x00\x00"
    s = sum(rom) & 0xFFFF
    rom[0x7FDC] = (s ^ 0xFFFF) & 0xFF; rom[0x7FDD] = (s ^ 0xFFFF) >> 8
    rom[0x7FDE] = s & 0xFF; rom[0x7FDF] = s >> 8
