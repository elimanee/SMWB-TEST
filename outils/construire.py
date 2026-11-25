#!/usr/bin/env python3
"""Construit la romhack « Super Mario World - Bretagne ».

Usage :  python3 outils/construire.py CHEMIN/Super_Mario_World_USA.sfc

Produit :
  build/SMW_Bretagne.sfc        la ROM modifiée (à ne pas publier)
  patch/SMW_Bretagne.bps        le patch à partager
  build/apercu_*.png            aperçus des textes avec la police du jeu
"""
import glob
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bps
import coiffe
import mariniere
import gfx
import messages
import noms_niveaux
from smwrom import CLEAN_SHA1, fix_checksum, snes_to_pc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_clean_rom(path):
    data = open(path, "rb").read()
    if len(data) % 0x8000 == 0x200:   # header copieur de 512 octets
        data = data[0x200:]
    sha = hashlib.sha1(data).hexdigest()
    if sha != CLEAN_SHA1:
        sys.exit("Cette ROM n'est pas une Super Mario World (USA) d'origine (SHA-1 %s).\n"
                 "Il faut la ROM propre, SHA-1 %s." % (sha, CLEAN_SHA1))
    return data


def apply_graphics(rom):
    """Dessins de graphismes/*.txt et couleurs de graphismes/palettes.txt."""
    folder = os.path.join(ROOT, "graphismes")
    files = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        if os.path.basename(path) == "palettes.txt":
            continue
        num, tiles, w, pix = gfx.parse_drawing(path)
        if num not in files:
            files[num] = gfx.read_gfx(rom, num)
        gfx.apply_drawing(files[num], tiles, w, pix)
        print("Dessin : %s" % os.path.basename(path))
    for num in coiffe.FILES:
        if num not in files:
            files[num] = gfx.read_gfx(rom, num)
    print("Coiffes bigoudènes : %d" % coiffe.apply(files))
    print(mariniere.apply(rom))
    for num in sorted(files):
        print("  " + gfx.write_gfx(rom, num, files[num]))
        assert gfx.read_gfx(rom, num) == files[num], "relecture GFX%02X différente" % num
    pal = os.path.join(folder, "palettes.txt")
    if os.path.exists(pal):
        for line in open(pal, encoding="utf-8"):
            line = line.split(";", 1)[0].strip()
            if not line:
                continue
            addr, rgb = line.split("=")
            r, g, b = (int(v) >> 3 for v in rgb.split(","))
            v = r | g << 5 | b << 10
            p = snes_to_pc(int(addr.strip(), 16))
            rom[p] = v & 0xFF; rom[p + 1] = v >> 8


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    clean = load_clean_rom(sys.argv[1])
    rom = bytearray(clean)

    names = noms_niveaux.parse_file(os.path.join(ROOT, "textes", "niveaux.txt"))
    size, counts = noms_niveaux.write_names(rom, names)
    print("Noms de niveaux : %d octets, morceaux %s" % (size, counts))
    assert {k: v for k, v in noms_niveaux.read_names(rom).items() if v} == \
        {k: v for k, v in names.items() if v}, "relecture des noms différente"

    msgs = messages.parse_file(os.path.join(ROOT, "textes", "messages.txt"))
    used = messages.write_messages(rom, msgs)
    print("Messages : %d octets sur %d" % (used, messages.SPACE))
    back = messages.read_messages(rom)
    for i, lines in msgs.items():
        assert [l.rstrip() for l in lines] == back[i], "relecture du message %d différente" % i

    apply_graphics(rom)

    fix_checksum(rom)
    rom = bytes(rom)

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "patch"), exist_ok=True)
    out_rom = os.path.join(ROOT, "build", "SMW_Bretagne.sfc")
    out_bps = os.path.join(ROOT, "patch", "SMW_Bretagne.bps")
    open(out_rom, "wb").write(rom)
    patch = bps.create(clean, rom)
    assert bps.apply(clean, patch) == rom, "le patch BPS ne redonne pas la ROM"
    open(out_bps, "wb").write(patch)
    print("ROM   : %s" % out_rom)
    print("Patch : %s (%d octets)" % (out_bps, len(patch)))

    try:
        import apercu
        apercu.messages_png(rom, {i: back[i] for i in msgs},
                            os.path.join(ROOT, "build", "apercu_messages.png"))
        apercu.names_png(rom, noms_niveaux.read_names(rom),
                         os.path.join(ROOT, "build", "apercu_niveaux.png"))
        print("Aperçus : build/apercu_messages.png, build/apercu_niveaux.png")
    except ImportError:
        print("(Pillow non installé : pas d'aperçus PNG)")


if __name__ == "__main__":
    main()
