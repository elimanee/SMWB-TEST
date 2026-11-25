#!/usr/bin/env python3
"""Captures d'écran automatiques de la ROM construite (nécessite : pip install stable-retro).

Usage :  python3 outils/captures.py            -> build/captures/*.png

Lance le jeu, va jusqu'au message d'intro, puis montre la carte du Pays
Bigouden (menhirs), la carte principale (phare), un château en ruines (drapeau,
via une ROM de test temporaire) et la scène de fin (coiffe de la Princesse).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "captures")
ROM = os.path.join(ROOT, "build", "SMW_Bretagne.sfc")

# Entrées Map16 de la carte : château Koopa et ruines (pour la ROM de test)
CHATEAU_MAP16 = (0x2D260, 0x2D530)
RUINES = bytes.fromhex("8A159A158B159B15")


def zoom(im, box, k):
    from PIL import Image
    c = im.crop(box)
    return c.resize((c.width * k, c.height * k), Image.NEAREST)


def run(rom, mode):
    from emu import Emu, patch_wram
    e = Emu(rom)
    # écran titre -> sélection du fichier -> 1 joueur -> message d'intro
    e.wait(300); e.press("START", after=60); e.press("A", after=60); e.press("A", after=60)
    e.press("A", frames=6, after=60); e.press("START", frames=6, after=300)
    intro = e.save_state()

    def carte(sub, pos=None):
        s = patch_wram(intro, 0x1F11, sub)
        if pos:
            for a, v in ((0x1F17, pos[0] & 255), (0x1F18, pos[0] >> 8),
                         (0x1F19, pos[1] & 255), (0x1F1A, pos[1] >> 8)):
                s = patch_wram(s, a, v)
        e.load_state(s); e.wait(2)
        from vram import blocks
        for _ in range(6):                       # jusqu'à l'affichage de la carte
            e.press("A", frames=6, after=200)
            if blocks(e.save_state())["RAM"][0x100] == 0x0E:
                break
        e.wait(200)

    if mode == "normal":
        e.shot(os.path.join(OUT, "01_intro.png"))
        carte(1)
        e.shot(os.path.join(OUT, "02_carte_pays_bigouden.png"))
        pays = e.save_state()
        carte(0, (0x100, 0x40))
        e.shot(os.path.join(OUT, "03_carte_principale.png"))
        zoom(e.screen(), (95, 25, 215, 95), 6).save(os.path.join(OUT, "04_phare.png"))
        # niveau Pays Bigouden 1 : Mario en marinière, puis Mario de feu + crêpe en réserve
        for nom, pouvoir, objet in (("08_niveau_mariniere.png", 1, 0), ("09_niveau_feu_crepe.png", 3, 1)):
            e.load_state(patch_wram(patch_wram(pays, 0x0DB8, pouvoir), 0x0DBC, objet)); e.wait(2)
            e.press("LEFT", frames=6, after=120); e.press("A", frames=6, after=300)
            e.shot(os.path.join(OUT, nom))
        e.load_state(patch_wram(pays, 0x0100, 0x1D)); e.wait(352)
        e.shot(os.path.join(OUT, "06_fin_princesse.png"))
        zoom(e.screen(), (190, 140, 240, 200), 8).save(os.path.join(OUT, "07_coiffe.png"))
    else:
        carte(1)
        zoom(e.screen(), (158, 48, 198, 88), 12).save(os.path.join(OUT, "05_drapeau_ruines.png"))


def main():
    if len(sys.argv) == 3:
        run(sys.argv[1], sys.argv[2]); return
    os.makedirs(OUT, exist_ok=True)
    rom = bytearray(open(ROM, "rb").read())
    for a in CHATEAU_MAP16:
        rom[a:a + 8] = RUINES
    test = os.path.join(ROOT, "build", "test_ruines.sfc")
    open(test, "wb").write(rom)
    # un seul émulateur par processus : un sous-processus par ROM
    subprocess.check_call([sys.executable, __file__, ROM, "normal"])
    subprocess.check_call([sys.executable, __file__, test, "ruines"])
    print("Captures dans", OUT)


if __name__ == "__main__":
    main()
