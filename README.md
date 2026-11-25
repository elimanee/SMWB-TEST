# Super Mario World — Bretagne

Romhack de *Super Mario World* (SNES, version US) sur le thème de la Bretagne :
Mario traverse le Pays Bigouden, les Monts d'Arrée, les grottes de Morgat,
Brocéliande, Ouessant et la Vallée de l'Ankou pour sauver la princesse.

## État actuel (version 0.1 : les textes)

- **Tous les noms de niveaux** de la carte : Ker Yoshi, Pays Bigouden 1-4,
  Monts d'Arrée, Maison de l'Ankou, Grottes de Morgat, Pont de Térénez,
  Lac de Guerlédan, Ménez Hom, Brocéliande, Tombeau de Merlin, Fontaine de
  Barenton, Val sans Retour, Île d'Ouessant, la Ville d'Ys, Carnac 1-5,
  Route des Menhirs, les châteaux (#1 Fort La Latte… #7 Fort de Fougères),
  et la Zone Spéciale en breton (Demat, Kenavo, Trugarez, Fest Noz,
  Kouign Amann, Gwenn ha Du, Yec'hed Mat, Krampouezh).
- **Tous les messages** (blocs d'info, intro, Yoshi, palais) réécrits en
  français, avec un peu de breton (« Degemer mat ! », « Chans vat ! »).

Liste complète : [`textes/niveaux.txt`](textes/niveaux.txt) et
[`textes/messages.txt`](textes/messages.txt).

## Jouer

1. Il faut sa propre ROM **Super Mario World (USA)** d'origine
   (SHA-1 `6b47bb75d16514b6a476aa0c73a683a2a4c18765`, sans header).
   La ROM n'est **pas** dans ce dépôt et ne doit pas y être publiée.
2. Appliquer le patch [`patch/SMW_Bretagne.bps`](patch/SMW_Bretagne.bps)
   avec [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)
   (dans le navigateur) ou Floating IPS / beat.
3. Lancer la ROM obtenue dans un émulateur (snes9x, bsnes, Mesen…).

## Reconstruire / modifier les textes

Prérequis : Python 3 (et `Pillow` pour les aperçus, facultatif).

```bash
python3 outils/construire.py chemin/vers/Super_Mario_World_USA.sfc
```

Cela produit `build/SMW_Bretagne.sfc` (la ROM, ignorée par git),
`patch/SMW_Bretagne.bps` (le patch à partager) et des aperçus
`build/apercu_messages.png` / `build/apercu_niveaux.png` dessinés avec la
vraie police du jeu, pour relire sans émulateur.

Pour changer un texte, il suffit de modifier `textes/niveaux.txt` ou
`textes/messages.txt` puis de relancer la commande. L'outil vérifie tout
(longueur des lignes, place disponible) et explique ce qui ne va pas.

Limites de la police d'origine : **pas d'accents** (ils sont retirés
automatiquement), **pas de 8 ni de 9**, pas de `:` ; ponctuation disponible :
`! . - , ? # ( ) '`. Noms de niveaux : 19 caractères max. Messages :
8 lignes de 18 caractères.

## Notes techniques

Zones de la ROM modifiées (aucun nouveau code ASM) :

| Zone | Contenu |
|---|---|
| `$04:9AC5-$04:9D06` | dictionnaire des mots des noms de niveaux et tables des morceaux 2 et 3 |
| `$04:9D30` | opérande de `LDA $9C91,Y` → la table des morceaux 1 est déplacée en `$04:A1B6` (128 entrées au lieu de 31) |
| `$04:A0FC-$04:A3FF` | nom de chaque niveau + espace libre d'origine (`$A1B6-$A3FF`, rempli de `$FF` dans la ROM US) |
| `$05:A5A7-$05:B0FE` | pointeurs et texte des messages |
| `$00:FFDC-$00:FFDF` | somme de contrôle recalculée |

Dans le jeu d'origine, un nom de niveau est l'assemblage de 3 morceaux pris
dans un petit dictionnaire de 459 octets ; `outils/noms_niveaux.py` découpe
et compresse automatiquement les noms pour qu'ils tiennent.

Si vous utilisez ensuite **Lunar Magic** sur la ROM patchée : faites-le pour
les niveaux, la carte et les graphismes, mais continuez d'éditer les noms de
niveaux et les messages avec ces outils (ou bien uniquement dans Lunar
Magic), sans mélanger les deux pour ces textes-là.

## Prochaines étapes possibles

Avec Lunar Magic (Windows) et les outils de SMW Central :

- **Graphismes** : drapeau Gwenn ha Du à la place des drapeaux de
  mi-parcours, menhirs et calvaires en décor, phares, coiffe bigoudène,
  crêpes / galettes comme objets.
- **Palettes** : landes violettes (bruyère) pour les Monts d'Arrée, granit
  rose, mer verte et grise pour Ouessant.
- **Carte** : retracer le monde aux contours de la péninsule bretonne.
- **Police** : ajouter é, è, à, ç dans des tuiles libres de GFX2A.
- **Musique** : airs de biniou / bombarde (addmusicK).
