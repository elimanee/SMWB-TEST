"""Noms des niveaux affichés sur la carte (overworld).

Dans la ROM d'origine, chaque nom = morceau1 + morceau2 + morceau3, chaque
morceau étant un mot d'un petit dictionnaire :
  - dictionnaire de mots : $04:9AC5, 0x1CB octets (+ un espace en $04:9C90
    utilisé par le jeu pour compléter la ligne), dernier caractère d'un mot | 0x80
  - table des morceaux 1 : $04:9C91 (31 entrées max)
  - table des morceaux 2 : $04:9CCF (15 entrées max)
  - table des morceaux 3 : $04:9CED (13 entrées max)
  - nom de chaque niveau  : $04:A0FC, 16 bits = (m1 << 8) | (m2 << 4) | m3
Le jeu n'affiche pas un morceau 1 d'un seul caractère, ni un morceau 2 = " ".
Un nom fait au plus 19 caractères.

Pour avoir plus de place, on déplace la table des morceaux 1 dans l'espace
libre de la banque 04 ($04:A1B6, 586 octets à $FF dans la ROM d'origine) en
changeant seulement l'adresse de l'instruction LDA $9C91,Y : elle passe de 31
à 128 entrées, et le reste de l'espace libre accueille des mots en plus. Les
offsets des mots sont relatifs à $04:9AC5, ils peuvent donc pointer là aussi.
Aucun nouveau code ASM.

Ce module découpe automatiquement des noms libres pour qu'ils tiennent dans
ces contraintes (petite recherche locale déterministe).
"""
import random

from smwrom import snes_to_pc, encode_text, decode_text, normalize

WORDS = snes_to_pc(0x049AC5)
SPACE_OFS = 0x1CB
T1_OPERAND = snes_to_pc(0x049D30)   # opérande de LDA $9C91,Y
T1_ORIG = snes_to_pc(0x049C91)
T1_NEW = 0x04A1B6                    # espace libre de la banque 04
FREE_END = 0x04A400                  # fin de la zone utilisée (libre jusqu'à $A400)
T2, T3 = snes_to_pc(0x049CCF), snes_to_pc(0x049CED)
N1, N2, N3 = 128, 15, 13
# zones où l'on peut écrire des mots : (offset depuis $04:9AC5, taille)
REGIONS = [(0, SPACE_OFS), (T1_NEW + 2 * N1 - 0x049AC5, FREE_END - T1_NEW - 2 * N1)]
LEVELS = snes_to_pc(0x04A0FC)
NB_TRANSLEVELS = 0x5D
MAX_LEN = 19


def read_names(rom):
    def w16(a):
        return rom[a] | rom[a + 1] << 8

    def word(o):
        t = []
        while True:
            b = rom[WORDS + o]; t.append(b); o += 1
            if b & 0x80:
                return t
    t1 = snes_to_pc(0x040000 | rom[T1_OPERAND] | rom[T1_OPERAND + 1] << 8)
    names = {}
    for tl in range(NB_TRANSLEVELS):
        v = w16(LEVELS + 2 * tl)
        a, b, c = (v >> 8) & 0x7F, (v >> 4) & 0xF, v & 0xF
        t = []
        w = word(w16(t1 + 2 * a))
        if not w[0] & 0x80:
            t += w
        w = word(w16(T2 + 2 * b))
        if w[0] != 0x9F:
            t += w
        t += word(w16(T3 + 2 * c))
        names[tl] = decode_text(t).rstrip()
    return names


def _splits(name):
    """Toutes les façons de couper un nom en 3 morceaux aux espaces."""
    toks, cur = [], ""
    for ch in name:
        cur += ch
        if ch == " ":
            toks.append(cur); cur = ""
    if cur:
        toks.append(cur)
    n = len(toks)
    res = []
    for i in range(n + 1):
        for j in range(i, n + 1):
            p1, p2, p3 = "".join(toks[:i]), "".join(toks[i:j]), "".join(toks[j:])
            if not p3:  # pas besoin d'espace final : le jeu complète la ligne
                if p2:
                    p2 = p2.rstrip()
                elif p1:
                    p1 = p1.rstrip()
            if p1 and len(p1) < 2:
                continue
            if p2 and p2.strip() == "":
                continue
            res.append((p1, p2, p3))
    return res


def _pack(words):
    """Range les mots (partage des suffixes, puis remplissage des zones libres).
    Renvoie (liste de (offset, octets), offsets, octets_en_trop)."""
    words = sorted(set(w for w in words if w), key=lambda w: (-len(w), w))
    offs, stored = {}, []          # stored : (mot, offset)
    free = [list(r) for r in REGIONS]
    chunks, over = [], 0
    for w in words:
        for (pw, po) in stored:
            if pw.endswith(w):
                offs[w] = po + len(pw) - len(w); break
        else:
            enc = encode_text(w, "nom de niveau")
            enc[-1] |= 0x80
            for r in free:
                if r[1] >= len(enc):
                    offs[w] = r[0]; chunks.append((r[0], enc))
                    r[0] += len(enc); r[1] -= len(enc)
                    break
            else:
                offs[w] = SPACE_OFS; over += len(enc)
            stored.append((w, offs[w]))
    return chunks, offs, over


def _cost(choice):
    s1, s2, s3 = {""}, {""}, {""}
    for (p1, p2, p3) in choice.values():
        s1.add(p1); s2.add(p2); s3.add(p3)
    chunks, _, over = _pack(s1 | s2 | s3)
    size = sum(len(c) for _, c in chunks) + over
    over += max(0, len(s1) - N1) + max(0, len(s2) - N2) + max(0, len(s3) - N3)
    return over * 1000 + size, size, (len(s1), len(s2), len(s3))
def solve(names, iterations=6000, seed=1):
    uniq = sorted(set(n for n in names.values() if n))
    for n in uniq:
        if len(encode_text(n, n)) > MAX_LEN:
            raise ValueError("Nom trop long (%d > %d) : %r" % (len(n), MAX_LEN, n))
    opts = {n: _splits(n) for n in uniq}
    rnd = random.Random(seed)
    # départ : premier mot en morceau 1, dernier mot en morceau 3
    choice = {}
    for n in uniq:
        choice[n] = max(opts[n], key=lambda s: (bool(s[0]), bool(s[2]), -len(s[0])))
    best = cur = _cost(choice)[0]
    best_choice = dict(choice)
    temp = 30.0
    for it in range(iterations):
        n = rnd.choice(uniq)
        old = choice[n]
        choice[n] = rnd.choice(opts[n])
        c = _cost(choice)[0]
        if c <= cur or rnd.random() < pow(2.718, (cur - c) / max(temp, 0.01)):
            cur = c
            if c < best:
                best, best_choice = c, dict(choice)
        else:
            choice[n] = old
        temp *= 0.999
    total, size, counts = _cost(best_choice)
    if total >= 1000:
        raise ValueError("Impossible de faire tenir les noms : %d octets (max %d), "
                         "morceaux %s (max %s). Raccourcissez ou réutilisez des mots."
                         % (size, sum(r[1] for r in REGIONS), counts, (N1, N2, N3)))
    return best_choice, size, counts


def write_names(rom, names):
    """names : {translevel: "NOM"}. Les translevels absents sont vidés."""
    choice, size, counts = solve(names)
    s1 = [""] + sorted({c[0] for c in choice.values()} - {""})
    s2 = [""] + sorted({c[1] for c in choice.values()} - {""})
    s3 = [""] + sorted({c[2] for c in choice.values()} - {""})
    chunks, offs, over = _pack(s1 + s2 + s3)
    assert not over
    offs[""] = SPACE_OFS
    t1 = snes_to_pc(T1_NEW)
    # efface l'ancienne zone de mots, l'ancienne table 1 et la zone libre utilisée
    rom[WORDS:WORDS + SPACE_OFS] = b"\xFF" * SPACE_OFS
    rom[T1_ORIG:T2] = b"\xFF" * (T2 - T1_ORIG)
    rom[t1:snes_to_pc(FREE_END)] = b"\xFF" * (FREE_END - T1_NEW)
    for o, enc in chunks:
        rom[WORDS + o:WORDS + o + len(enc)] = bytes(enc)
    rom[WORDS + SPACE_OFS] = 0x9F
    rom[T1_OPERAND] = T1_NEW & 0xFF; rom[T1_OPERAND + 1] = (T1_NEW >> 8) & 0xFF
    for base, lst, cap in ((t1, s1, N1), (T2, s2, N2), (T3, s3, N3)):
        for i in range(cap):
            o = offs[lst[i]] if i < len(lst) else SPACE_OFS
            rom[base + 2 * i] = o & 0xFF; rom[base + 2 * i + 1] = o >> 8
    for tl in range(NB_TRANSLEVELS):
        n = names.get(tl, "")
        if n:
            p1, p2, p3 = choice[n]
            v = (s1.index(p1) << 8) | (s2.index(p2) << 4) | s3.index(p3)
        else:
            v = 0
        rom[LEVELS + 2 * tl] = v & 0xFF; rom[LEVELS + 2 * tl + 1] = v >> 8
    return size, counts


def parse_file(path):
    names = {}
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split(";", 1)[0].rstrip()
        if not line.strip():
            continue
        tl, _, name = line.partition("=")
        name = name.strip().upper()
        # accents non disponibles dans la police : lettre simple
        names[int(tl.strip(), 16)] = normalize(name)
    return names
