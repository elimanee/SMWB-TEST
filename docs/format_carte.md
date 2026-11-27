# Données de la carte du monde (overworld) — notes de décodage

Notes de rétro-ingénierie de la ROM Super Mario World (USA), relevées avec
`outils/desasm.py`. Elles servent à quiconque voudrait déplacer des niveaux sur la
carte. Adresses SNES (LoROM). Une « case » fait 16x16 pixels. La carte
principale fait 32x32 cases. Les sous-cartes partagent une seconde zone de
32x32 cases.

## Couche 1 (niveaux, chemins, icônes)

- Données de départ : 0x800 octets bruts en `$0C:F7DF`, un octet par case.
  Le jeu les copie en RAM `$7E:C800` (`MVN` en `$04:DC58`). Cette couche contient
  dès le départ **tous** les chemins, même ceux pas encore débloqués.
- Index d'une case : `0x200·(y≥16) + 0x100·(x≥16) + (y%16)·16 + x%16`, plus
  0x400 pour la zone des sous-cartes.
- Les tuiles 0x56 à 0x80 sont des tuiles de niveau.

## Numérotation des niveaux (translevels)

Le jeu numérote les niveaux en `$04:D7F2`. Il parcourt `$7E:C800` dans l'ordre de
l'index (quart haut-gauche, haut-droit, bas-gauche, bas-droit, puis les
sous-cartes) et donne à chaque tuile de niveau le numéro suivant. Ces numéros
sont écrits en `$7E:D000`. Le niveau n°N charge le niveau N (ou N+0xDC). Il
indexe aussi les noms, les messages, la progression et les événements.

**Conséquence :** déplacer un niveau qui change cet ordre de parcours fait
charger le mauvais niveau. Pour s'en affranchir, il faut remplacer `LDA $00` en
`$04:D83C` par une lecture dans une table « rang → numéro » (environ 15 octets de
code, par exemple via un `JSL`).

`$04:D678` contient un octet par numéro de niveau, copié en `$7E:D800`.

## Événements (chemins qui s'ouvrent)

Il y a 0x6F événements. Leurs drapeaux sont en `$1F02`, et le masque de bit en
`$04:E44B`. Au chargement, `$04:DA49` rejoue chaque événement déjà fait.

| Table | Contenu |
|---|---|
| `$04:D85D` | 1 mot par événement : index couche 1 de la tuile de niveau qui change d'aspect. La tuile est cherchée dans `$04:DA1D` (22 tuiles) et remplacée par `$04:DA33`. |
| `$04:E5D6` / `$04:E5B6` | 16 événements, chacun avec un index couche 1. Tuiles cherchées : `$04:E5A7`, remplacées par `$04:E5AC` et, une case plus bas, par `$04:E5B1` (château détruit…). |
| `$04:E8E4` / `$04:E910` / `$04:E93C` / `$04:E994` | 0x2C entrées : événement, drapeau, position, tuile. Si le drapeau a le bit 0 à 0 : tuile de couche 1 posée à l'index donné. Si le bit 0 est à 1 : bloc 16x16 de couche 2, posé à l'offset en octets dans `$7F:4000`. |
| `$04:E359` | 1 mot par événement : début de sa plage dans la liste suivante (la fin est l'entrée suivante). |
| `$04:DD8D` / `$04:DD8F` | Liste des blocs de couche 2 révélés par les événements, 4 octets par entrée : tuile 16x16, puis offset dans `$7F:4000` (2 × index de la tuile 8x8 en haut à gauche). |

## Couche 2 (relief)

Elle est stockée compressée en RLE : les tuiles en `$04:A533`, les propriétés en
`$04:C02B` (voir `outils/carte.py`). En RAM, elle est en `$7F:4000` : 64x64
tuiles 8x8, en 4 pages de 32x32.

## Passages et téléportations

| Table | Contenu |
|---|---|
| `$04:8431` / `$04:8467` | 27 départs (tuyaux, routes des menhirs) : case x (sous-carte dans l'octet haut) et case y. |
| `$04:849D` / `$04:84D3` | Arrivées en pixels (centre de case). Les bits 9 et plus de x donnent la sous-carte. |
| `$04:9964`… (5 octets × 14) | Passages carte ↔ sous-cartes par les bords : y et x en pixels, puis la sous-carte. L'arrivée est en `$04:99AA`, la case d'arrivée en `$04:99F0`. |
| `$04:8E49` / `$04:8E4F` | 3 positions de réapparition particulières. |

## Ce que cela implique pour la carte bretonne

Les chemins de la carte principale occupent presque toute sa hauteur (lignes 2
à 29). L'île du sud (monde 6) est reliée au château n°5 par un chemin
vertical. Les chemins d'eau de la baie (route des menhirs du lac de Guerlédan)
et ceux des Monts d'Arrée la bloquent aussi. Déplacé d'un bloc, sans redessiner
ses chemins, ce monde ne peut remonter que de 2 ou 3 cases. Pour l'installer
dans la baie, il faudrait redessiner tout son réseau de chemins et les données
d'événements qui vont avec.
