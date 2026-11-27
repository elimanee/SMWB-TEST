"""Carte du monde (overworld), couche 2 : relief (terre, mer, falaises...).

Stockée en deux flux compressés en RLE dans la ROM :
  - numéros de tuiles  : $04:A533 (6904 octets dans la ROM d'origine)
  - attributs (palette, retournements) : $04:C02B (5709 octets)
Chaque flux donne $2000 octets : 4 pages de 32x32 pour la carte principale
(64x64 tuiles de 8x8 = 512x512 pixels), puis 4 pages pour les sous-cartes.
Les deux flux se suivent ; l'adresse du second est dans le code en $04:DC8C
(opérande de LDA #$C02B), mise à jour quand les flux changent de taille.
Format RLE : octet n ; si n & $80 : répéter l'octet suivant (n & $7F) + 1 fois,
sinon copier les n + 1 octets suivants.

La forme « Bretagne » de la carte principale est décrite dans
carte/bretagne_cases.txt (une case modifiée par ligne : x y mot_hexa), générée
par outils/carte_bretagne.py.
"""
import os

from smwrom import snes_to_pc, pc_to_snes

TILES = snes_to_pc(0x04A533)
PROPS = snes_to_pc(0x04C02B)
# opérande de « LDA #$C02B » ($04:DC8C) : adresse du flux des attributs
PROPS_OPERAND = 0x025C8D
SIZE = 0x2000
SPACE = {TILES: PROPS - 4 - TILES, PROPS: None}


def rle_decode(rom, pc, n=SIZE):
    out = bytearray(); start = pc
    while len(out) < n:
        c = rom[pc]; pc += 1
        if c & 0x80:
            out += bytes([rom[pc]]) * ((c & 0x7F) + 1); pc += 1
        else:
            out += rom[pc:pc + c + 1]; pc += c + 1
    assert len(out) == n
    return bytearray(out), pc - start


def rle_encode(data):
    out = bytearray(); i = 0; lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:128]; del lit[:128]
            out.append(len(chunk) - 1); out.extend(chunk)
    n = len(data)
    while i < n:
        j = i
        while j < n and j - i < 128 and data[j] == data[i]:
            j += 1
        if j - i >= 3:
            flush(); out.append(0x80 | (j - i - 1)); out.append(data[i]); i = j
        else:
            lit.append(data[i]); i += 1
    flush()
    return bytes(out)


def index(x, y):
    """Position (x, y) de la carte principale -> index dans les flux."""
    return ((y // 32) * 2 + (x // 32)) * 0x400 + (y % 32) * 32 + x % 32


def apply(rom, cases_path):
    lo, used_lo = rle_decode(rom, TILES)
    hi, used_hi = rle_decode(rom, PROPS)
    n = 0
    for line in open(cases_path, encoding="utf-8"):
        line = line.split(";", 1)[0].split()
        if len(line) != 3:
            continue
        x, y, w = int(line[0]), int(line[1]), int(line[2], 16)
        i = index(x, y)
        lo[i] = w & 0xFF; hi[i] = w >> 8; n += 1
    clo, chi = rle_encode(lo), rle_encode(hi)
    assert rle_decode(clo, 0)[0] == lo and rle_decode(chi, 0)[0] == hi
    # les deux flux se suivent : place totale = celle des deux flux d'origine ;
    # le flux des attributs est écrit juste après celui des tuiles et le code
    # qui le charge est mis à jour
    space = (PROPS - TILES) + used_hi
    if len(clo) + len(chi) > space:
        raise ValueError("Carte : flux trop gros (%d octets, place %d)" % (len(clo) + len(chi), space))
    assert rom[PROPS_OPERAND] == 0x2B and rom[PROPS_OPERAND + 1] == 0xC0
    rom[TILES:TILES + space] = b"\xFF" * space
    rom[TILES:TILES + len(clo)] = clo
    new = TILES + len(clo)
    rom[new:new + len(chi)] = chi
    a = pc_to_snes(new)
    assert a >> 16 == 0x04
    rom[PROPS_OPERAND] = a & 0xFF; rom[PROPS_OPERAND + 1] = (a >> 8) & 0xFF
    return "Carte : %d cases, %d octets compressés (place %d), attributs en $%06X" % (
        n, len(clo) + len(chi), space, a)
