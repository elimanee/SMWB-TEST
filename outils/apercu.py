"""Aperçus PNG des textes, dessinés avec la vraie police de la ROM (GFX2A).
Permet de relire le résultat sans lancer d'émulateur."""
from PIL import Image

from smwrom import lz2_decompress, gfx_file_pc, encode_text

PAL = [(0, 0, 0), (0, 0, 0), (120, 120, 120), (248, 248, 248)]
BG = (0, 0, 0)


def _font(rom):
    return lz2_decompress(rom, gfx_file_pc(rom, 0x2A))


def _tile(img, gfx, t, px, py, scale):
    for y in range(8):
        b0, b1 = gfx[t * 16 + y * 2], gfx[t * 16 + y * 2 + 1]
        for x in range(8):
            c = ((b0 >> (7 - x)) & 1) | (((b1 >> (7 - x)) & 1) << 1)
            if c:
                for k in range(scale * scale):
                    img.putpixel((px + x * scale + k % scale, py + y * scale + k // scale), PAL[c])


def render_lines(rom, lines, scale=2, pad=8):
    gfx = _font(rom)
    w = max(18, max(len(encode_text(l)) for l in lines))
    img = Image.new("RGB", (w * 8 * scale + 2 * pad, len(lines) * 8 * scale + 2 * pad), BG)
    for row, l in enumerate(lines):
        for col, t in enumerate(encode_text(l)):
            _tile(img, gfx, t & 0x7F, pad + col * 8 * scale, pad + row * 8 * scale, scale)
    return img


def sheet(images, cols, gap=6, label=None):
    w = max(i.width for i in images); h = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols
    out = Image.new("RGB", (cols * (w + gap) + gap, rows * (h + gap) + gap), (40, 40, 40))
    for k, im in enumerate(images):
        out.paste(im, (gap + (k % cols) * (w + gap), gap + (k // cols) * (h + gap)))
    return out


def messages_png(rom, msgs, path):
    imgs = [render_lines(rom, msgs[i]) for i in sorted(msgs) if i not in (1, 2, 3)]
    sheet(imgs, 4).save(path)


def names_png(rom, names, path):
    seen, lines = set(), []
    for tl in sorted(names):
        n = names[tl]
        if n and n not in seen:
            seen.add(n); lines.append(n)
    half = (len(lines) + 1) // 2
    imgs = [render_lines(rom, lines[:half]), render_lines(rom, lines[half:])]
    sheet(imgs, 2).save(path)
