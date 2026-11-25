"""Lecture d'un état snes9x (stable-retro) : VRAM, WRAM et palette, et rendu
des couches de fond tuile par tuile, pour savoir quelles tuiles/palettes le jeu
utilise réellement à l'écran."""
import re

from PIL import Image


def blocks(state):
    out = {}
    for m in re.finditer(rb"([A-Z][A-Z0-9]{2}):(\d{6}):", state):
        n = int(m.group(2))
        out.setdefault(m.group(1).decode(), state[m.end():m.end() + n])
    return out


class Snap:
    def __init__(self, state):
        b = blocks(state)
        self.vram = b["VRA"]
        self.wram = b["RAM"]
        pal = self.wram[0x0703:0x0903]          # copie de la palette par SMW
        self.cg = [self.col(pal[2 * i] | pal[2 * i + 1] << 8) for i in range(256)]

    @staticmethod
    def col(v):
        return ((v & 31) * 8, ((v >> 5) & 31) * 8, ((v >> 10) & 31) * 8)

    def tile4(self, t):
        b = (t * 32) & 0xFFFF
        v = self.vram
        rows = []
        for y in range(8):
            r = []
            for x in range(8):
                s = 7 - x
                r.append(((v[b + y * 2] >> s) & 1) | (((v[b + y * 2 + 1] >> s) & 1) << 1) |
                         (((v[b + 16 + y * 2] >> s) & 1) << 2) | (((v[b + 17 + y * 2] >> s) & 1) << 3))
            rows.append(r)
        return rows

    def layer(self, map_word_addr, w=64, h=32, base_char=0, mark=None):
        """Rendu d'un tilemap 4bpp (adresse VRAM en mots). Couleur 0 = magenta."""
        img = Image.new("RGB", (w * 8, h * 8), (255, 0, 255))
        px = img.load()
        for ty in range(h):
            for tx in range(w):
                # tilemaps 64x32 = deux écrans 32x32 côte à côte
                scr = tx // 32
                a = (map_word_addr + scr * 0x400 + ty * 32 + tx % 32) * 2
                e = self.vram[a] | self.vram[a + 1] << 8
                t, pal = e & 0x3FF, (e >> 10) & 7
                hf, vf = e & 0x4000, e & 0x8000
                tile = self.tile4(base_char + t)
                for y in range(8):
                    for x in range(8):
                        c = tile[7 - y if vf else y][7 - x if hf else x]
                        if c:
                            px[tx * 8 + x, ty * 8 + y] = self.cg[pal * 16 + c]
        return img

    def entry(self, map_word_addr, tx, ty):
        scr = tx // 32
        a = (map_word_addr + scr * 0x400 + ty * 32 + tx % 32) * 2
        return self.vram[a] | self.vram[a + 1] << 8
