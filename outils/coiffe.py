"""Remplace la couronne de la Princesse par une coiffe bigoudène.

Repère automatiquement chaque couronne (motif de la rangée du haut
2 1 2 1 1 2 1 2) dans les fichiers GFX de la Princesse, et dessine à la place
une haute coiffe de dentelle blanche. Palette de la Princesse :
1 blanc, 2 noir, 3 brun, 4 doré, 5 jaune pâle, 6 peau, 7 rose."""

CROWN_TOP = [2, 1, 2, 1, 1, 2, 1, 2]
CROWN_MID = [2, 1, 5, 1, 1, 5, 1, 2]
FILES = (0x22, 0x24, 0x26)


def _img(tiles):
    return [[tiles[(y // 8) * 16 + x // 8][y % 8][x % 8] for x in range(128)] for y in range(64)]


def _store(tiles, img):
    for t in range(128):
        tiles[t] = [[img[(t // 16) * 8 + y][(t % 16) * 8 + x] for x in range(8)] for y in range(8)]


def find_crowns(img):
    found = []
    for y in range(64):
        for x in range(128 - 8):
            if img[y][x:x + 8] == CROWN_TOP and y + 1 < 64 and img[y + 1][x:x + 8] == CROWN_MID:
                found.append((x, y))
    return found


def draw(img, x, y0):
    # lignes vides au-dessus de la couronne (dans le même sprite) : on monte la coiffe
    k = 0
    while k < 2 and y0 - k - 1 >= 0 and y0 - k - 1 >= (y0 // 16) * 16 and \
            all(img[y0 - k - 1][c] == 0 for c in range(x + 1, x + 7)):
        k += 1
    top = y0 - k
    # efface les bords de la couronne qui dépassent de la coiffe
    for row, cols in ((y0, (x, x + 7)), (y0 + 1, (x, x + 7, x + 8))):
        for c in cols:
            if img[row][c] in (1, 2, 5):
                img[row][c] = 0
    bottom = y0 + 5
    for row in range(top, bottom + 1):
        if row == top:
            line = [0, 2, 2, 2, 2, 0]          # sommet arrondi
        elif row == bottom:
            line = [2, 5, 5, 5, 5, 2]          # ruban à la base
        else:
            line = [2, 1, 1, 1, 1, 2]          # haute dentelle blanche
        for i, c in enumerate(line):
            if c:
                img[row][x + 1 + i] = c
            elif row == top and img[row][x + 1 + i] in (1, 2, 5):
                img[row][x + 1 + i] = 0


def draw_help(img):
    """Princesse « HELP! » dans la Clown Car (GFX24) : petite couronne à la main."""
    for row, line in ((0, [0, 2, 2, 2, 0]), (1, [2, 1, 1, 1, 2]),
                      (2, [2, 1, 1, 1, 2]), (3, [2, 5, 5, 5, 2])):
        for i, c in enumerate(line):
            if c:
                img[row][50 + i] = c


def apply(rom_files):
    """rom_files : {num: tuiles} (modifié sur place). Renvoie le nombre de coiffes."""
    n = 0
    for num in FILES:
        img = _img(rom_files[num])
        crowns = find_crowns(img)
        for (x, y) in crowns:
            draw(img, x, y)
        if num == 0x24 and img[2][50:55] == [5, 1, 5, 1, 5]:
            draw_help(img)
            n += 1
        _store(rom_files[num], img)
        n += len(crowns)
    return n
