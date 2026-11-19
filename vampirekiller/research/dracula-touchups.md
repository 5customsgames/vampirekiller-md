# Dracula 16 bits : retouches (stage 18, salle 9)

**Etat : retenu par l'utilisateur et applique** : 1B/5B (`head-b`), 2B (`cape-b`), 3A/7A (`sickle-a`), 6B (`bat-b`) et 8B (palette chaude du visage, `vk_dracula_view_begin`). **Non retenu** : 1A/5A, 2A, 3B/7B, 6A, 8A, 4A (pulsation, un mot de CRAM par image) et 4B (rien a faire). Le generateur applique l'ensemble retenu par defaut (`dracula_touchups.RETAINED`) ; `--variant none` redonne l'art d'avant. Le texte ci-dessous est celui de la proposition (le « rien n'est livre » ne vaut plus).

Document de proposition. Rien n'est livre : `generated/dracula16_md.*` et le jeu sont inchanges (le generateur sans `--variant` produit
des fichiers identiques octet pour octet). Les retouches sont des variantes de `tools/build_dracula16.py`, ecrites ailleurs que dans
`sgdk/src/generated/` :

```
python tools/build_dracula16.py <castlevania-md> --variant head-b,cape-b,bat-b,sickle-a --out-dir /chemin/sortie [--preview f.png]
python tools/dracula_touchups_board.py <castlevania-md> <capture_salle_sans_dracula.png> <dossier> [head cape sickle bat all fade face]
```

Variantes : `head-a head-b cape-a cape-b bat-a bat-b sickle-a sickle-b`, plus `all-a` et `all-b`. Le code des dessins est
`tools/dracula_touchups.py` (images en niveaux 0 a 7 par canal, comme le reste du generateur).

## Contraintes tenues par toutes les propositions

- Memes 24 cellules de 16 x 16 (96 tuiles, 3 072 octets), memes boites, memes poses, memes 65 composites de buste, meme SAT, memes
  transferts : seuls les pixels changent. Aucun cout par image dans le code de combat, sauf la proposition 4A (signalee).
- Entrees 8 (rouge 020E) et 14 (blanc 0EEE) de la palette PAL2 conservees (silhouette de Simon, `actors.c load_simon_color`).
- La palette est rechoisie par variante (choix glouton du generateur, entrees 1 a 15 hors 8 et 14). La boule rouge compte plus dans
  ce choix pour les variantes (poids x10) : sans cela le reflet rose de la boule devenait bleute.
- Mesures dans le jeu (ROM de variante construite hors de `sgdk/src/generated/`, harnais Genesis Plus GX) : meme nombre d'images
  (3 898 sur le scenario de capture, 2 608 du debut de la salle a la mort sur `zzze`), meme taille de ROM.

## Defauts, propositions A et B, couts

Numerotation des defauts : 1 tete qui flotte, 2 cape en blocs, 3 faucilles rouges et anguleuses, 4 palette fixe (pas de fondus MSX),
5 capuche vide, 6 chauves-souris (3 images pour 4 poses), 7 faucilles (4 images pour 6 poses), 8 visage de fond inchange.

| Prop. | Defaut | Principe | ROM | Temps | Risque |
|---|---|---|---|---|---|
| 1A / 5A (`head-a`) | tete, capuche | cellule capuchon (2 et 6, deja dans la chaine de sprites, dessinee par-dessus la tete) : haut col de cape en pointe derriere la tete, col bas devant, cou noir sous le menton | 0 octet (memes cellules) | 0 | tres faible ; erreur de palette 3,1 (inchangee) |
| 1B / 5B (`head-b`) | tete, capuche | meme cellule : capuche rouge symetrique a liseré dore, doublure noire contre le visage, col rouge | 0 | 0 | tres faible ; erreur 3,2 |
| 2A (`cape-a`) | cape | memes epaules et chaine d'or, reste redessine : plis courbes eclaires par la gauche, bande noire de droite supprimee, bas du manteau en dents ; manteau ouvert en V (doublure sombre a plis, pan plisse a droite) | 121 -> 113 tuiles uniques du buste : -256 octets | 0 | faible ; memes 4 rouges |
| 2B (`cape-b`) | cape | idem mais cape evasee jusqu'aux 32 colonnes des cellules, ourlet ondule plus profond | 121 -> 127 : +192 octets | 0 | faible ; erreur 3,0 |
| 3A / 7A (`sickle-a`) | faucilles | croissant d'acier (lame a reflet blanc, liseré sombre, manche brun) dessine par rastérisation sur-echantillonnee puis tourne de 60 degres par cellule : six images distinctes (18 a 23), fond noir opaque de l'image Castlevania-MD supprime | 0 | 0 | moyen : choisie seule elle degrade la palette (erreur 3,1 -> 5,8) ; dans l'ensemble recommande l'erreur redescend a 2,6 |
| 3B / 7B (`sickle-b`) | faucilles | memes six rotations en rouge sombre a liseré pale | 0 | 0 | faible ; erreur 3,3 |
| 4A (code, a part) | palette fixe | pulsation du violet de la tete (entree 6 de PAL2) en 18 etats, comme la pulsation de la palette MSX (`palette[12..13]`, `ce[57]` en seconde forme) : un mot de CRAM par image en seconde forme (`vk_dracula_view_pass`, une dizaine de lignes) | ~40 octets de code | ~0,1 % d'une image, seulement en seconde forme | faible ; viole « aucun cout par image » : optionnel |
| 4B | palette fixe | ne rien faire pour le fondu final : au moment du fondu MSX (etat 9) il ne reste aucun sprite de Dracula a l'ecran, un fondu de PAL2 ne se verrait pas | 0 | 0 | aucun |
| 6A (`bat-a`) | chauves-souris | la 4e pose (cellule 17, copie de la 15) devient la chauve-souris a plat de la cellule 14 avec les ailes remontees (cisaillement des colonnes) | 0 | 0 | tres faible |
| 6B (`bat-b`) | chauves-souris | quatre phases d'un battement redessinees (haut, descente, bas, montee) : corps, oreilles, yeux rouges (entree 8), membranes | 0 | 0 | faible ; plus sombres et plus petites que l'original ; erreur 2,6 (meilleure) |
| 8A / 8B (palette seule) | visage de fond | rehaussement de la rampe de peau : 8A froide et cendree, 8B chaude a la torche (planche `planche_8_visage.png`) | +96 octets (palette initiale en octets MSX de 32 + couleurs PAL0 de 32) | 0 | faible : a installer a `vk_dracula_view_begin` quand `vk_gfx16`, la palette `d->palette` etant copiee d'une table 16 bits au lieu de `vk_dracula_initial_palette` ; le fondu de fin et la pulsation de l'entree 6 travaillent sur les memes octets ; texte des credits (entree 14) non touche |

Detail technique de 7 : `dracula_poses.h` donne 6 poses de faucille (types 44, poses 27 a 32) sur 6 cellules ; le generateur de
base les remplissait avec `b7_sickle0..3` (i mod 4), donc les deux dernieres etaient des doublons. 3A et 3B remplissent les six.
Pour 6 : les poses 2, 165, 166, 167 donnent `obj_42, obj_43, obj_41, obj_43` dans la base (cellules 14, 15, 16, 17).

## Verification

- Planches (a tuiles quantifiees a la palette de chaque variante, posees sur le fond reel de la salle, agrandies x5 ou x8) :
  `build/dracula-touchups/planche_*.png` de ce worktree (non versionne) : `planche_1_5_tete_capuche`, `planche_2_cape`,
  `planche_3_7_faucilles`, `planche_4_palette`, `planche_6_chauves_souris`, `planche_8_visage`, `planche_ensemble`
  (actuel / tout A / tout B / ensemble recommande) ; en jeu : `planche_ingame_dracula` et `planche_ingame_forme2` (MSX / 16B actuel /
  ensemble recommande, memes images du scenario).
- Ensemble recommande construit en ROM et rejoue en jeu : `zzze_gfx16_dracula.txt` passe 15 assertions sur 17. Les deux echecs
  sont attendus : la couleur exacte du violet de la tete (205, 101, 238, devenue (172, 101, 238)) et « faucilles et chauves-souris dans
  le rouge de la palette 16 bits » (les faucilles sont d'acier). A mettre a jour si l'ensemble est adopte, ainsi que
  `tests/test_dracula16.py` (fichier genere a jour) et la section « Dracula 16 bits » de `gfx16.md`.

## Recommandation

Ensemble `head-b,cape-b,bat-b,sickle-a` (+ 8B) : c'est lui qui est construit et rejoue ci-dessus.

1. 3A / 7A (faucilles d'acier a six rotations) : le gain le plus visible, aucun cout, regle deux defauts.
2. 2B (cape evasee) puis 1B / 5B (capuche rouge) : la silhouette cesse d'etre une tete posee sur des rectangles ; 0 a +192 octets.
3. 6B (quatre phases de chauve-souris) : meilleure erreur de palette ; 6A si l'on veut garder le dessin de Castlevania-MD.
4. 8B (visage) : sans cout d'execution, a prendre si le ton chaud plait (8A change l'ambiance vers le violet).
5. 4A (pulsation) : seulement si un mot de CRAM par image en seconde forme est acceptable ; 4B : rien a faire.

Ordre d'adoption conseille : 3, 2, 1, 6, 8, 4A. Chaque variante est independante (a l'exception de la palette, rechoisie pour
l'ensemble : regenerer et rejouer `zzze` apres chaque combinaison).
