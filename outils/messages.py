"""Boîtes de message (blocs « ! » d'information, Yoshi, intro...).

Format dans la ROM d'origine :
  - $05:A591 : 22 octets, translevel de chaque message (bit 7 = 2e message du niveau)
  - $05:A5A7 : 25 offsets 16 bits (relatifs à $05:A5D9) ; 0-3 = palais à bouton
  - $05:A5D9 : texte, 8 lignes de 18 tuiles max par message, la dernière
               tuile d'une ligne a le bit 7 mis (le jeu complète avec des espaces)
Place disponible pour le texte : $05:A5D9-$05:B0FE (2854 octets).
"""
from smwrom import snes_to_pc, encode_text, decode_text

PTRS = snes_to_pc(0x05A5A7)
TEXT = snes_to_pc(0x05A5D9)
SPACE = 2854
NB = 25
WIDTH, LINES = 18, 8


def read_messages(rom):
    msgs = []
    for i in range(NB):
        y = TEXT + (rom[PTRS + 2 * i] | rom[PTRS + 2 * i + 1] << 8)
        lines = []
        for _ in range(LINES):
            t = []
            for _ in range(WIDTH):
                b = rom[y]; y += 1; t.append(b)
                if b & 0x80:
                    break
            lines.append(decode_text(t).rstrip())
        msgs.append(lines)
    return msgs


def wrap(text, where):
    """Découpe un texte en lignes de 18 caractères. '|' force un retour à la ligne,
    une ligne commençant par '=' est recopiée telle quelle (espaces compris)."""
    out = []
    for para in text:
        if para.startswith("="):
            out.append(para[1:]); continue
        for chunk in para.split("|"):
            line = ""
            for w in chunk.split():
                if len(encode_text(w, where)) > WIDTH:
                    raise ValueError("%s : mot trop long %r" % (where, w))
                cand = (line + " " + w) if line else w
                if len(encode_text(cand, where)) <= WIDTH:
                    line = cand
                else:
                    out.append(line); line = w
            out.append(line)
    if len(out) > LINES:
        raise ValueError("%s : %d lignes (max %d) :\n  %s" % (where, len(out), LINES, "\n  ".join(out)))
    for l in out:
        if len(encode_text(l, where)) > WIDTH:
            raise ValueError("%s : ligne trop longue %r" % (where, l))
    return out + [""] * (LINES - len(out))


def parse_file(path):
    """Fichier texte : '[NN] titre' puis le texte du message jusqu'au suivant."""
    msgs, cur = {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith(";"):
            continue
        if line.startswith("["):
            cur = int(line[1:line.index("]")])
            msgs[cur] = []
        elif cur is not None and line.strip():
            msgs[cur].append(line if line.startswith("=") else line.strip())
    res, errors = {}, []
    for k, v in msgs.items():
        try:
            res[k] = wrap(v, "message %d" % k)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise ValueError("\n".join(errors))
    return res


def write_messages(rom, msgs):
    """msgs : {index: [8 lignes]}. Les index 0 à 3 (palais) partagent un texte."""
    orig = read_messages(rom)
    final = [msgs.get(i, orig[i]) for i in range(NB)]
    for i in (1, 2, 3):
        final[i] = final[0]
    blob, ptr, seen = bytearray(), [], {}
    for lines in final:
        key = tuple(lines)
        if key not in seen:
            seen[key] = len(blob)
            for l in lines:
                t = encode_text(l, "message") if l else encode_text(" ")
                while len(t) > 1 and t[-1] == 0x1F:   # espaces finaux inutiles
                    t.pop()
                if len(t) < WIDTH:
                    t[-1] |= 0x80
                blob += bytes(t)
        ptr.append(seen[key])
    if len(blob) > SPACE:
        raise ValueError("Messages trop longs : %d octets (max %d)" % (len(blob), SPACE))
    rom[TEXT:TEXT + SPACE] = bytes(blob) + b"\xFF" * (SPACE - len(blob))
    for i, p in enumerate(ptr):
        rom[PTRS + 2 * i] = p & 0xFF; rom[PTRS + 2 * i + 1] = p >> 8
    return len(blob)
