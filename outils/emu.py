"""Pilote d'émulateur (stable-retro / snes9x) pour faire des captures d'écran
automatiques de la ROM :  pip install stable-retro

    from emu import Emu
    e = Emu("build/SMW_Bretagne.sfc")
    e.wait(300); e.press("START"); e.shot("titre.png")
"""
import warnings

import numpy as np
from PIL import Image

warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    import stable_retro as retro
except ImportError:
    import retro

BUTTONS = ["B", "Y", "SELECT", "START", "UP", "DOWN", "LEFT", "RIGHT", "A", "X", "L", "R"]


class Emu:
    def __init__(self, rom):
        self.em = retro.RetroEmulator(rom)
        self.frame = 0

    def wait(self, frames=1, hold=()):
        mask = np.array([1 if b in hold else 0 for b in BUTTONS], dtype=np.uint8)
        for _ in range(frames):
            self.em.set_button_mask(mask, 0)
            self.em.step()
            self.frame += 1

    def press(self, *buttons, frames=4, after=20):
        self.wait(frames, hold=buttons)
        self.wait(after)

    def screen(self):
        return Image.fromarray(self.em.get_screen())

    def shot(self, path, scale=2):
        im = self.screen()
        im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(path)

    def ram(self):
        return self.em.get_state()

    def save_state(self):
        return self.em.get_state()

    def load_state(self, s):
        self.em.set_state(s)


def patch_wram(state, addr, value):
    """Modifie un octet de WRAM ($7E:xxxx) dans un état snes9x."""
    import re as _re
    m = _re.search(rb"RAM:(\d{6}):", state)
    off = m.end() + addr
    s = bytearray(state)
    s[off] = value
    return bytes(s)
