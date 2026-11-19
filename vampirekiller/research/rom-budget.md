# Budget ROM : place dans la collection 4 Mio et gains possibles

Etude ; les etapes 1 et 2 de la recommandation sont faites depuis (section 6 : -52 992 o, 182 300 o libres). Les sections 1 a 5 gardent les mesures de l'etude.

Etat mesure : worktree a92816c (`sgdk/out/rom.out`, `make GDK=...`, SGDK 2.11, GCC `-O3 -flto`).
Outils ajoutes par cette etude : `tools/rom_budget.py` (inventaire + `--check`), `tests/run_rom_budget.sh`
(0,1 s, lit l'ELF existant), `tools/rom_compress_probe.py` (compression mesuree avec les jars SGDK et cout
de decompression 68000 modelise). Aucune donnee du jeu, aucun fichier de `sgdk/src` n'a ete touche.

**Mise a jour 2026-11-16 : etape 3 faite** (format de musique a motifs, 2.1 et `research/audio-driver.md` 6.1). Mesure sur `47f6401` puis apres
(`tools/rom_budget.py`) : image 1 885 924 -> 1 704 164 o (-181 760), **libre dans la collection 129 308 -> 311 068 o (303,8 Kio)** ;
`make collection` : libre 0x1F918 -> 0x4BF18 apres Vampire Killer. Les autres chiffres des sections 1 a 3 restent ceux de l'etude (a92816c).

## 1. La place restante

La collection (`vampirecollection-md`, `Makefile`, `collection/merge_rom.py`) met Castlevania-MD a 0 et Vampire Killer
a `VK_BASE = 0x214000`, sans mapper : Vampire Killer doit finir avant `0x400000`.

| element                                             | octets    |
|-----------------------------------------------------|----------:|
| plafond de Vampire Killer = 0x400000 - 0x214000     | 2 015 232 |
| image Vampire Killer (`objcopy -O binary`), liee a 0 | 1 885 668 |
| idem liee a `VK_BASE` avec `vk.ld` de la collection (mesure, build temporaire) | 1 885 672 |
| **libre**                                           | **129 564 (126,5 Kio)** |

Castlevania-MD finit a 0x211C04 (`out/collection/castlevania.bin`, 2 169 860 o) : 9 212 o de marge sous `VK_BASE`.
Le chiffre « ~30 Kio » de la demande ne se retrouve pas : meme en comptant la ROM remplie a 128 Kio
(`rom.bin` = 0x1E0000), il resterait 49 152 o. Le dernier `vampirekiller.bin` de la collection (17:13, sources plus anciennes) faisait
1 954 540 o (60 692 libres) : les sources de `main` ont depuis perdu ~69 Kio. `tools/rom_budget.py` relit `VK_BASE` dans le Makefile de la collection
(`VK_COLLECTION=...`, ou `VK_BASE=0x...` pour un autre plafond) ; `--check [--margin N]` echoue si la place libre est sous N.

Repartition (nm, `tools/rom_budget.py --top 5`) :

| categorie       | Kio   | %     | gros symboles |
|-----------------|------:|------:|---------------|
| cartes          | 463,2 | 25,2  | vk_maps 214 016, late_maps 64 512, vk_stageN_collision 60 672, g16_*_map 109 120 (155 x 704) |
| code (+petites tables) | 357,4 | 19,4 | vk_show_player 23 702, Enemies_frame 22 100, main 16 316, step_boss 16 132, vk_step_enemies 15 668 |
| tuiles 16 bits  | 267,9 | 14,5  | vk_gfx16_pool 194 272 (69 856 depuis l'etape 4, 2.4), vk_intro16_sprites 26 868 |
| son FM          | 220,1 | 12,0  | msx_fm_80..8e 195 779 + msx_fm_noise_* 29 233 |
| sprites         | 205,1 | 11,1  | vk_dracula_bust_sets 33 280, jeux de poses Simon (shield, whip, crouch) ~80 Ko |
| tuiles MSX      | 172,3 |  9,4  | vk_tiles 43 008, vk_stageN_tiles 56 832, scene_tiles 34 272, vk_intro_frames 15 360 |
| son PSG         |  69,8 |  3,8  | msx_sound_80..8e 68 271 (musiques du mode PSG) |
| PCM             |  34,2 |  1,9  | wilhelm_pcm 35 072 |
| SGDK            |  31,5 |  1,7  | vsprintf 4 602, drv_pcm 2 866 |
| autres          |  19,8 |  1,1  | vk_palettes 4 864, textes |

(`nm` ne distingue pas le code d'une petite table : la categorie « code » contient quelques Kio de tables.)

## 2. Mesures par bloc

Methode : octets reels de l'ELF, compresses par `lz4w.jar p` et `apj.jar pp` (aPLib maximum) ; le decodeur aPLib du modele est verifie octet pour
octet contre l'original, le modele LZ4W relit la longueur decompressee. Cout = cycles 68000 de `lz4w_unpack` / `aplib_unpack` de `tools_a.s`
comptes sur les flux reels (instruction par instruction, sans etats d'attente, +-15 %) ; ligne = 488 cycles, image = 262 lignes (~128 000 cycles).
LZ4W : 7 a 13 cycles par octet (la doc SGDK dit 550-950 Ko/s, soit 8 a 14) ; aPLib : 33 a 165 cycles par octet selon le contenu
(cartes ~66-100, tuiles ~90-150), soit 8 a 12 fois plus lent.

RAM libre : `_bend` = 0xFFC199, il reste 15 975 o jusqu'au haut de la pile (pile SGDK comprise) : un tampon de decompression est limite a ~6-8 Kio.

### Tableau recapitulatif

| bloc (taille)                                     | technique                              | gain mesure | cout | moment | risque |
|---------------------------------------------------|----------------------------------------|------------:|------|--------|--------|
| `msx_fm_*` + `msx_fm_noise_*` (225 012)           | **motifs d'images** : appel (3 o) vers une suite d'images deja ecrite, plus repetition d'images vides (1 o) | **fait : -144 590** (fm -121 695, bruit -22 895) | +0,4 ligne en moyenne par pas (mesure), 6 o de RAM | en jeu, V-Int | fait, decodage identique teste |
| idem, LZ4W en flux par blocs de 4 Kio             | decompresser la musique en tampon      | -182 000 (aPLib -196 000) | 4 Kio x ~9 c/o = ~76 lignes par bloc toutes les ~3-6 s ; 2 tampons de 4 Kio | en jeu | eleve : pointes de 76 lignes, RAM |
| `msx_sound_8x` (68 271, mode PSG)                 | motifs d'images (meme code)            | **fait : -37 449** | +0,4 ligne en moyenne par pas (mesure) | en jeu | fait (meme format) |
| `vk_gfx16_pool` (194 272)                         | **coherence de palette** + doublons exacts (generateur seul) : **fait** (2026-11-16) | **-124 416 mesure** (6 071 -> 2 183 tuiles, voir 2.4) | 0 a l'execution | build | fait : rendu identique verifie (hors ligne et emulateur) |
| idem                                              | miroirs H/V/HV                          | -4 300 (136 tuiles) | 0 mais cartes u8 -> u16 (+109 Ko) | | a ecarter |
| idem                                              | LZ4W / aPLib du pool entier            | -61 000 / -94 500 | tampon 3 a 23 Kio impossible (RAM), 226 / 3 346 lignes par etage | | a ecarter |
| `vk_maps` (214 016, u16 dont l'octet haut est 0)  | u16 -> u8                              | -107 008 | ~0 (boucle d'ecriture de carte, voir 2.3) | dessin de salle | moyen (calibrage du dessin hors gel) |
| idem + LZ4W par salle (704 o)                     | u8 puis LZ4W                           | -175 800 (aPLib -179 500) | 18,8 lignes / salle (max 24,9) ; aPLib 148 | dessin de salle, ecran coupe | moyen |
| `late_maps` 64 512 + `vk_stageN_collision` 60 672 | LZ4W par salle (768 o) en tampon RAM de 768 o | -45 400 et -38 700 | 18,6 / 20,8 lignes par salle (max 26,6 / 27,4) | entree de salle | moyen : lues a chaque image par le jeu |
| `g16_*_map` (109 120, u8, 155 x 704)              | LZ4W par salle                         | -69 500 (aPLib -72 800) | 18,6 lignes / salle (max 25,1) ; aPLib 147 | dessin de salle (g16), ecran coupe | faible a moyen |
| `vk_dracula_bust_sets` (33 280)                   | **65 tuiles uniques sur 1 040** : 65 tuiles + 65 listes de 16 index | -30 200 | ~6 lignes par changement de buste (copie de 16 tuiles, 512 o, vers `row_words`) | salle de Dracula, a chaque changement de couches | faible |
| idem                                              | LZ4W par jeu de 512 o                  | -8 000 | 11,7 lignes (decompression) | | a ecarter |
| `wilhelm_pcm` (35 072)                            | reechantillonnage 11 025 Hz (+ queue silencieuse coupee) | -17 400 ; -22 700 coupe a 1,1 s ; 8 000 Hz coupe : -26 000 | 0 | chute de Simon | faible (timbre) |
| idem                                              | supprimer (et `drv_pcm` 2 866 + `SND_PCM_*` ~550) | -38 500 | 0 | | choix de produit |
| `vk_intro16_sprites` 26 868 + `vk_intro_frames` 15 360 | LZ4W par blocs de 2 Kio / 768 o   | -19 200 / -12 000 | 47 / 14 lignes par bloc, une fois toutes les 16 images | introduction | faible (aucun jeu en cours) |
| `vk_tiles` (43 008, 7 x 6 144)                    | LZ4W / aPLib par jeu                   | -15 200 / -23 100 | 143 / 1 808 lignes par jeu, tampon 6 Kio | dessin de salle (mode MSX) | eleve pour peu |
| `vk_stageN_tiles` (56 832, etages 12-18)          | LZ4W / aPLib par jeu                   | -42 100 / -44 900 | 212 / 1 481 lignes par jeu (max 293 / 2 188), tampon 6-9 Kio | idem | eleve |
| `scene_tiles_*` (34 272) ; `vk_stageN_enemy_tiles` (28 672) | LZ4W / aPLib par bloc        | -14 600 / -20 500 ; -17 000 / -20 700 | 122 / 72 lignes par bloc | scene / entree de salle | moyen |
| poses de Simon (`vk_simon16_*` 40 736, MSX ~40 000, DMA par pose) | LZ4W                  | -30 200 pour les 16 bits | 61 lignes par pose, chargees en jeu | **en jeu, a chaque pose** | a ecarter |
| code : `-Os` global                                | -214 000 (texte 1 885 544 -> 1 671 528) | -- | code plus lent | | eleve (timing) |
| code : `-O2` global                                | -140 000                               | -- | | | eleve |
| code : `-O3 -fno-inline-functions`                 | -84 000                                | -- | | | moyen |
| code : `-Os` sur les seuls fichiers froids         | -13 500                                | -- | | menus, carte, test du son, scenes | faible |
| `vsprintf` (SGDK, 4 602) | remplacer par un formatage de nombres | -4 000 | 0 | | faible |

### 2.1 Musiques (FM 225 Kio, PSG 68 Kio)

Les flux (`msx_fm_md.h`) sont lus vers l'avant a 60 Hz : par image un octet de comptage puis des paires registre/valeur ; la boucle est un decalage d'octets.
Compresses entiers, ils tombent a 11 % (LZ4W) et 6 % (aPLib), les bruits a 5,7 % : ils sont tres repetitifs. Mais une decompression
entiere est impossible en RAM (35 Kio pour le plus gros), et par blocs la repetition lointaine se perd (1 Kio : 34 %, 2 Kio : 25 %, 4 Kio : 19 % en LZ4W).

Le gain sans decompression vient d'un format a motifs. Simulation (script jetable, non commite ; glouton, sources litterales seulement donc profondeur d'appel 1) : decouper
chaque flux en images, remplacer toute suite d'au moins 4 images deja ecrite par un appel de 3 octets (image de depart sur 2 octets, longueur) et toute serie de 3 images identiques
d'un octet (silences) par 2 octets. Resultat (plus petit seuil 3 ; resultats presque identiques de 3 a 12) :

| flux             | avant   | apres   | gain    |
|------------------|--------:|--------:|--------:|
| FM (msx_fm_8x)   | 195 779 |  80 651 | 115 128 |
| bruits (noise)   |  29 233 |   7 551 |  21 682 |
| PSG (msx_sound_8x) | 68 271 |  28 329 |  39 942 |

Dans le lecteur, une suite d'appel de 3 octets coute un test par image (FM : `n` <= 63, les octets 0x40.. sont libres ; PSG et bruit : les bits 6-7 de l'entete sont des drapeaux, il faut un code d'echappement libre, par exemple un comptage de 63 jamais produit, a verifier) et une pile d'un retour ;
aucune RAM, aucune pointe de temps. FM et bruit avancent images pour images ensemble (`vk_fm_core_step`) : le meme codage doit s'appliquer aux deux, avec une image
de boucle qui demarre un segment litteral.

**Fait (2026-11-16)** : `tools/music_motif.py` (compacteur glouton et lecteur de reference), appele par `tools/build_msx_sound_md.py` apres la conversion ; lecteur dans
`psg_core.c` / `psg_core_fm.c` / `fm_core.c` (`music_frame`). Format retenu (detail : `research/audio-driver.md` 6.1) :
- PSG et bruit : le convertisseur ecrit au plus 14 octets par image, donc le bit 5 de l'entete (comptage >= 32) est libre et marque un code : `001ooooo oooooooo n` = appel
  de `n` images (1 a 255) a l'octet `o` (13 bits ; les flux compactes font au plus 5,7 Kio), 3 octets ; `011kkkkk` / `101kkkkk` / `111kkkkk` = serie de `k + 1` images vides
  d'entete 00 / 40 / 80, 1 octet ;
- FM : `0x80..0xFE hi lo` = appel de `b - 0x7F` images (1 a 127), 3 octets ; `0x40..0x7F` = serie de `(b & 0x3F) + 1` images vides, 1 octet ;
- une serie est un appel dans une table fixe `vk_psg_runs` (192 o, 3 lignes de 64 images vides) : un seul mecanisme (pointeur de retour + compteur, 6 o de RAM par lecteur) ;
  un appel ne vise que des images simples ecrites a la suite : un seul niveau, pas de recursion ; l'image de boucle commence un code du niveau haut.

| flux             | avant   | apres   | gain    | simulation de l'etude |
|------------------|--------:|--------:|--------:|--------:|
| FM (msx_fm_8x)   | 195 779 |  74 084 | 121 695 | 115 128 |
| bruits (noise)   |  29 233 |   6 338 |  22 895 |  21 682 |
| PSG (msx_sound_8x) | 68 271 |  30 822 |  37 449 |  39 942 |
| total            | 293 283 | 111 244 | 182 039 | 176 752 |

Image : -181 760 o (table et code compris). Cout mesure (ROM de mesure `VK_MEASURE_PSG`, memes scripts avant/apres) : pas moyen du lecteur 4,18 -> 4,57 lignes en mode PSG,
6,30 -> 6,73 en mode FM ; pire cas observe 15,5 -> 15,9 (PSG) et 26,4 -> 27,1 lignes (FM). Rejeu 12-18 image exacte : 0 image perdue (55 points de controle) ; compare tour par tour a `47f6401` : marge minimale -10 -> -9 lignes, les memes 54 tours sous 6 lignes avant et apres (stage 12 salle 6, stage 15 salle 9 : deja sous la marge de 6 lignes avant ce changement), mediane 106 inchangee.
Decodage identique verifie par `tests/test_music_motif.py` (meme coeur sur flux simples et compactes : memes ecritures PSG et YM2612 a chaque pas, chaque musique sur
deux boucles en PSG et FM, plus 8 suites aleatoires de 60 000 pas avec effets, pause, FB, fondu, arret) et, une fois, contre le coeur et les flux de `47f6401` (2,8 millions de pas identiques).

### 2.2 `wilhelm_pcm` (fait, section 6.1)

Utilise uniquement par `main.c:921` (cri a la chute de Simon, `SND_PCM_startPlay` ; ajout du portage absent de la ROM MSX) et le pilote Z80 `drv_pcm`
charge au demarrage (`main.c:704`). Le Z80 lit la ROM directement : aucune decompression possible (LZ4W 78 %, aPLib 66 %, de toute facon). Le signal : 8 bits, 22 050 Hz, 1,59 s ;
99 % de l'energie sous 3,5 kHz, 99,9 % sous 5,3 kHz ; les derniers ~30 % de la duree (apres 1,1 s) sont a amplitude <= 3/127 (queue d'extinction). Donc 11 025 Hz (`SOUND_PCM_RATE_11025`) divise la taille par deux
sans perte audible utile ; couper la queue apres 1,1 s en gagne encore 5 Kio. Alignement 256 o a conserver.

### 2.3 Cartes

`vk_maps` : `const u16 vk_maps[152][704]`, mais toutes les valeurs sont < 192 (octet haut toujours 0, verifie par `rom_compress_probe.py --lowbyte`).
Lectures : `room_view.c` (`VDP_setTileMapDataRectEx`, dessin de salle en mode MSX qui est le mode par defaut, `vk_gfx16 = 0`), `item_view.c` (`room_map`, 4 cellules pour la cle de l'etage 2),
`gfx16.c vk_room_cell` (mode MSX seulement). Passer a u8 demande une boucle d'ecriture comme `vk_gfx16_draw_map` : elle existe deja pour les cartes 16 bits et son cout est le meme que celui des
salles 16 bits. La difference de duree du dessin hors gel (reapparition, debut d'etage, saut : calibre sur l'ancienne duree, `research/room-draw-budget.md`) est a mesurer avant de generaliser.
Les cartes 16 bits (`g16_*_map`, u8) different de `vk_maps` sur 23 % des cellules (82 368 / 107 008 egales) : un codage par difference ne fait pas mieux que LZ4W.

`late_maps` / `vk_stageN_collision` (768 o par salle) sont lues par le jeu a chaque image (`vk_late_room_map`, `gameplay.c`) : un tampon RAM de 768 o rempli a l'entree de salle convient (le tampon doit
rester valide tant que l'ancienne salle sert pendant un passage de porte : a verifier dans `room_manager.c`).

### 2.4 `vk_gfx16_pool` (194 272 o, 6 071 tuiles)

Les tuiles sont deja uniques (aucun doublon exact). Mesures :
- miroirs H/V/HV : 5 935 tuiles distinctes (-136, -4 352 o) ; les cartes contiendraient les bascules (u16 au lieu de u8 : +109 Ko) : perdant.
- aPLib 51 %, LZ4W 68 % : le pool serait a decompresser par etage (19 groupes de 3,4 a 22,8 Kio, tampon de 22 Kio impossible), 3 346 lignes par etage en moyenne (8 123 au pire).
- **Les memes dessins existent en plusieurs « teintes d'indices »** : le generateur donne a chaque salle sa propre palette (15 couleurs + noir), les tuiles qui ne different que par
  l'ordre des indices ne sont pas fusionnees. Converties en RGB, il n'y a que 2 914 tuiles exactes distinctes (par etage ; 2 179 en tout, 2 850 a un miroir pres) pour 6 071 dans le pool,
  soit 93 248 o au lieu de 194 272. Faire coherentes les palettes d'un etage (meme couleur = meme indice dans toutes ses salles) exige un coloriage de graphe des couleurs par etage :
  les etages ont 15 a 24 couleurs (hors noir) pour 15 indices ; un coloriage glouton passe sur 9 groupes sur 19 et demande 16-17 indices sur les autres (un coloriage exact ou une fusion de
  couleurs proches devra le resoudre ; les salles non resolues gardent leurs tuiles propres). Gain realiste : ~95 Kio, zero cout d'execution. Le rendu reste identique en RGB, mais la CRAM et les index VRAM changent.

**Fait (2026-11-16)** : `share_indices` de `tools/build_gfx16.py`. Pas de coloriage par etage (un coloriage exact a 15 indices, DSatur avec retour arriere, ne conclut pas en 5 s sur 9 etages sur 19 :
les salles a 15 couleurs imposent toutes leurs indices ; et fusionner des couleurs changerait l'image) : chaque salle garde sa palette de 15 couleurs au plus et choisit l'ordre de ses indices qui retrouve le plus de tuiles deja
rangees par les autres salles (votes sur les paires couleur -> indice des encodages existants de ses tuiles ; couleurs restantes : indice de leur premiere salle), puis chaque
salle est rechoisie contre toutes les autres (depart vide ou depuis l'ordre d'une salle du meme etage) jusqu'a stabilite (3 passes, 15 s de generation en tout).
Le partage n'est pas limite a l'etage : une tuile commune a deux blocs (ciel, noir, MSX) est aussi fusionnee, et deux dessins RGB differents qui tombent sur les memes indices aussi,
d'ou un pool sous le compte des tuiles RGB distinctes (2 234).

| mesure                                   | avant     | apres     | gain     |
|------------------------------------------|----------:|----------:|---------:|
| `vk_gfx16_pool` (tuiles)                 | 6 071     | 2 183     | -3 888   |
| `vk_gfx16_pool` (octets)                 | 194 272   | 69 856    | -124 416 |
| image Vampire Killer (`rom_budget.py`)   | 1 885 924 | 1 761 508 | -124 416 |
| libre dans la collection                 | 129 308   | 253 724   | +124 416 |

Cout d'execution inchange : memes emplacements, memes cartes, meme nombre de tuiles par salle ecrites par `vk_gfx16_load_tiles` (le pool est deja lu tuile par tuile), code identique (366 109 o).
Seules les tuiles de la salle lisent PAL0 en mode 16 bits (`VK_PAL_OBJ`, `VK_PAL_ITEM`, PAL3 pour Simon) : les entrees reservees de PAL1/PAL2 (HUD, objets, ennemis, boss du stage 3) ne sont pas touchees ;
l'entree 0 reste noire (couleur de fond 0), l'indice 0 transparent. Verification : `tools/check_gfx16_render.py ANCIEN.c NOUVEAU.c` (chaque emplacement et la carte de chaque salle, 9 bits par pixel :
identiques), `tests/test_gfx16_render.py` (empreintes du rendu d'avant, `tests/data/gfx16_render.json`), captures de l'emulateur des 153 salles des stages 1 a 18 en mode 16 bits identiques entre l'ancienne et la nouvelle ROM.

### 2.5 Blocs de la salle de Dracula et de l'introduction

`vk_dracula_bust_sets` (fait, section 6.2) : 65 jeux de 16 tuiles (65 combinaisons ordonnees des couches 1..4) ; compresses ensemble 4,7 % (LZ4W), mais seulement 65 tuiles distinctes parmi 1 040 (33 a un miroir pres) :
le code (`dracula_view.c bust`) peut copier les 16 tuiles du jeu dans `row_words` (tampon de 1 Kio existant) puis `VDP_loadTileData` en DMA en file, ~5-7 lignes de plus que le DMA seul, loin des 50 a 120 lignes de la composition d'origine.

`vk_intro16_sprites`, `vk_intro_frames` : lus dans l'ordre du temps par `scene.c` (4 478 sprites 16 bits, 320 images) ; un bloc de 2 Kio decompresse tous les ~16 images pendant l'introduction (aucune logique de jeu, aucune
salle) : 47 lignes (sprites), 14 lignes (images) dans un tour de 250.

### 2.6 Code

Texte 1 885 544 o ; `code` ~366 Kio. Variantes mesurees (build LTO complet dans un dossier temporaire, taille seulement) :

| options                                              | texte     | gain    |
|------------------------------------------------------|----------:|--------:|
| actuel : `-O3 -flto` (SGDK)                          | 1 885 544 | 0       |
| `-O3 -fno-ipa-cp-clone`                              | 1 884 776 | -768    |
| `-O3 -fno-inline-functions`                          | 1 801 576 | -84 000 |
| `-O3 -fno-inline-functions -fno-ipa-cp-clone`        | 1 798 248 | -87 300 |
| `-O3` sans peel/unswitch/inline/cp-clone             | 1 782 120 | -103 400 |
| `-O2`                                                | 1 745 512 | -140 000 |
| `-O2 -fno-inline-functions`                          | 1 719 912 | -165 600 |
| `-Os`                                                | 1 671 528 | -214 000 |

Pourquoi les fonctions sont si grosses : `-O3` ajoute `-finline-functions` (toute fonction `static` appelee de plusieurs endroits est copiee dans chaque appelant : `vk_show_player` inline les sprites de chaque type d'ennemi,
23 702 o en `-O3`, 8 816 en `-Os` ; `Enemies_frame` 22 100 -> 12 434 ; `vk_step_weapons` 11 684 -> 3 864 ; `dracula_step` 11 448 -> 5 096 ; `vk_step_enemies` 15 668 -> 10 370 ; `main` 16 316 -> 11 718), le deroulage/pelage de boucles
et le « unswitch ». Les `.constprop.N` (clones d'appel a argument constant, `-fipa-cp-clone`) ne sont pas en cause : les desactiver ne gagne que 768 o. Au niveau des fichiers (compilation sans LTO,
`.text` seul) : enemies.c 79 700 -> 32 308 (-Os) / 52 098 (-O2), boss.c 37 700 -> 11 742 / 18 078, actors.c 25 356 -> 15 938 / 21 802, candles.c 22 900 -> 7 838 / 10 190, dracula.c 20 150 -> 5 906 / 7 442,
hud.c 13 662 -> 2 842 / 3 486, main.c 13 672 -> 8 660 / 12 824, gameplay.c 11 614 -> 4 440, player.c 10 152 -> 3 858 ; au total 327 428 o en `-O3`, 200 834 en `-O2`, 137 440 en `-Os`.

Ce chiffre est une taille, pas une vitesse. Les fonctions chaudes (tour de jeu, `vk_show_player`, ennemis, boss, `vk_step_*`) sont celles qui gagnent le plus et celles dont le timing compte : marge minimale 6 lignes
sur les salles 12-17, rejeu 12-18 image exacte, dessin de salle calibre (`research/room-draw-budget.md`, `sgdk/src/profile.h`). Tout changement de code doit etre verifie par
`vk_late_turns` / `vk_last_slack` sur les memes scenarios avant d'etre accepte. Les fichiers froids (carte d'etage `stage_map.c` 5 988 -> 1 304, `stage_map_view.c` 4 640 -> 2 070, `scene.c`,
`stageNN_scene.c`, `item_reveal_view.c`, `sound_test.c`, `stage12_secret.c`) donnent -13 500 o en `-Os` sans toucher au temps de jeu (`__attribute__((optimize("Os")))` par fonction ou drapeau par fichier ;
`__attribute__((noinline))` sur les gros corps rares : attaques du boss, fins, boutiques).

## 3. Cout de decompression en lignes d'ecran

Une image = 262 lignes ; le dessin de salle pendant le gel tient en 2 images (n_room_draw_margin exige <= 4), budget 7 : ~1 300 lignes de marge (hors rejeu calibre). La decompression
ne sert que si elle a lieu :

- **ecran coupe, dans le gel** (dessin de salle : `vk_gfx16_draw_map`, tuiles, cartes `g16_*_map`/`vk_maps`, tampon de 704 a 768 o) : 19 a 27 lignes par salle en LZ4W, 150 a 220 en aPLib : tient, avec la reserve que les dessins hors gel
  (reapparition, debut d'etage, saut d'etage, boss) ont un tour de dessin calibre sur l'ancienne duree (zzj_ghost5, zzb_stage8 : le tour de dessin compte pour un pas de jeu).
- **en jeu, sur une image** : LZ4W jusqu'a 20-30 lignes de pointe par bloc est a comparer a la marge minimale de 6 lignes des salles 12-17 : a eviter ; aPLib (80-150 c/o) impossible.
- **introduction** : aucune contrainte de jeu, 14 a 47 lignes.
- **a l'octet pret, sans decompression** (motifs de musique, doublons de tuiles, u8, palettes) : 0 a 7 lignes.

## 4. Recommandation, gains sûrs d'abord

| # | action | gain | cout / risque |
|---|--------|-----:|---------------|
| 1 | **fait** (section 6) PCM : 11 025 Hz, queue coupee (`wilhelm.json` / `wilhelm.pcm` regeneres) | -22 784 | 0 ; seul le timbre change |
| 2 | **fait** (section 6) Salle de Dracula : 65 tuiles + listes d'index (`build_dracula_background.py`, `dracula_view.c`) | -30 140 | +7 a 10 lignes mesurees par changement de buste ; image identique |
| 3 | **Fait** : format de musique a motifs (appel + repetition d'images vides) pour FM, bruit et PSG | -144 590 (+37 449 PSG) mesure ; image -181 760 | +0,4 ligne par pas en moyenne ; `fm_core`/`psg_core`, decodage identique teste |
| 4 | **Fait (2026-11-16)** : generateur, indices de palette partages entre salles et pool fusionne (`build_gfx16.py share_indices`) | -124 416 mesure (estime ~ -95 000) | 0 a l'execution ; image identique, CRAM/VRAM differents ; 135 scenarios MD passent sans changement |
| 5 | `vk_maps` u8 (+ `vsprintf` remplace, `-Os` sur les fichiers froids) | -107 000 ; -4 000 ; -13 500 | boucle d'ecriture a chronometrer ; le reste sans effet de jeu |
| 6 | Introduction : LZ4W par blocs (sprites, images) | -31 000 | 14 a 47 lignes pendant l'intro |
| 7 | Cartes de collision/16 bits en LZ4W par salle (`late_maps`, `vk_stageN_collision`, `g16_*_map`) | -84 000 ; -69 500 | 19 a 27 lignes au chargement de salle, tampon de 768 o ; a valider salle par salle sur le rejeu 12-18 |
| 8 | Code `-O2` sur tout (ou `-O3 -fno-inline-functions`) | -140 000 (-84 000) | seulement apres mesure du timing (rejeu 12-18, marge 6 lignes) |
| 9 | Supprimer le cri Wilhelm et le pilote PCM | -38 500 | decision de produit |

Les etapes 1 a 5 donnent ~ -300 000 o (sans les mesures de temps, tous ces gains sont a cout de jeu nul) et laissent ~ 430 Kio libres dans la collection contre 126,5 Kio aujourd'hui ;
les etapes 6 a 8 ne servent qu'en dernier recours. A ne pas faire : miroirs du pool 16 bits, compression des poses de Simon (chargees a chaque pose), aPLib en jeu.

## 5. Reproduire

```
python3 tools/rom_budget.py --top 5                  # inventaire ; --check [--margin N]
tests/run_rom_budget.sh                              # test (ne reconstruit que si sgdk/out/rom.out manque)
python3 tools/rom_compress_probe.py --unit 1408 vk_maps              # LZ4W/aPLib + cycles
python3 tools/rom_compress_probe.py --lowbyte --unit 1408 vk_maps    # u16 dont l'octet haut est 0 -> u8
python3 tools/rom_compress_probe.py --per-symbol 'vk_stage??_tiles'
python3 tools/convert_wilhelm.py /chemin/Wilhelm_Scream.ogg [--check]   # cri de Wilhelm 11 025 Hz (etape 1)
python3 tools/build_dracula_background.py [--check]                     # buste de Dracula dedoublonne (etape 2)
```

## 6. Etapes 1 et 2 faites (2026-11-16)

`tools/rom_budget.py`, ROM normale (`make vk`), avant (`main` 47f6401) / apres :

| element                         | avant     | apres     | ecart    |
|---------------------------------|----------:|----------:|---------:|
| image Vampire Killer            | 1 885 924 | 1 832 932 | -52 992  |
| `wilhelm_pcm`                   |    35 072 |    12 288 | -22 784  |
| `vk_dracula_bust_sets` -> `vk_dracula_bust_unique` 2 080 + `vk_dracula_bust_index` 1 040 | 33 280 | 3 120 | -30 160 |
| `bust` (code)                   |       360 |       380 | +20      |
| **libre dans la collection**    | **129 308** | **182 300 (178,0 Kio)** | +52 992 |

`make collection` : Vampire Killer 0x1BF7E8 octets a 0x214000, libre 0x2C818 (182 296 o) apres lui.

### 6.1 Cri de Wilhelm (etape 1)

`tools/convert_wilhelm.py` (nouveau, meme chaine FFmpeg que `castlevania/tools/convert_wilhelm.py` : volume 0,9, fondu d'entree 3 ms, tramage triangulaire)
reconvertit la source Commons (empreinte `360097c9...` verifiee ; l'ancien outil de Castlevania-MD redonne bien, octet pour octet, l'ancien PCM 22 050 Hz) :
11 025 Hz, 48 blocs de 256 o (12 288 o, 1,115 s ; l'alignement de 256 o du pilote est garde sans octet de bourrage), fondu de sortie 30 ms. `--check` compare aux fichiers
versionnes (sortie deterministe). `main.c` joue le son avec `SOUND_PCM_RATE_11025` : hauteur et duree inchangees (correlation 0,9993 avec l'ancien PCM pris un echantillon sur
deux). La queue coupee etait a <= 3/127 apres 1,1 s. Aucun pixel ne change (scenarios de la section 6.2 rejoues avec ce seul changement : 0 image differente).

### 6.2 Buste de Dracula (etape 2)

`tools/build_dracula_background.py` produit toujours les 65 composites, puis n'en garde que les 65 tuiles distinctes (`vk_dracula_bust_unique[65][8]`) et, par composite,
16 index (`vk_dracula_bust_index[65][16]`) ; le generateur verifie que les 65 x 16 tuiles reconstruites sont les composites d'avant (et `--check` est lance par
`tests/run_dracula_trace.sh`). `dracula_view.c bust` copie les 16 tuiles dans `row_words` (tampon de 1 Kio existant ; les credits, son autre utilisateur, ne tournent
jamais dans la meme passe et vident la file DMA avant d'y ecrire) puis met en file le meme DMA de 16 tuiles. La copie d'une tuile est une structure de 32 o : GCC en fait
8 `move.l (a0)+,(a1)+` ; la boucle des 16 tuiles est gardee roulee (`GCC unroll 1`), deroulee GCC ecrit a des adresses absolues (28 cycles par mot, 2,2 Ko de code).

Cout mesure (harnais Genesis Plus GX, `vk_last_slack` lu a chaque image, meme ROM avec et sans l'etape 2, memes entrees) : **7 a 10 lignes (mediane 9)** de marge en moins
au tour d'un changement de buste (30 a 62 changements par scenario), au lieu des 5 a 7 estimees (indexation et appel compris). Premiere version (copie mot par mot, registres
puis memoire) : 10 a 13 lignes. Marge restante au tour d'un changement : 70 lignes au pire (77 avant, `zzr_dracula_sablier_decor`), 91 a 95 dans les autres scenarios ;
le premier buste est pose par `vk_dracula_view_begin` dans le tour de dessin de la salle 9 (deja sur plusieurs images, marge -5 avant comme apres). Tours en retard, images
perdues hors dessin et tours absorbes identiques avant/apres sur toute la duree des 4 scenarios (`zzp_stage18` 118/59/43, `zzzc_gfx16_screens` 94/45/44, `zzr_dracula_*` 32/19/2) :
le cout tient dans le budget d'image (~250 lignes par tour, marge minimale exigee 6 lignes, `research/room-draw-budget.md`).

Image : chaque image des scenarios `zzp_stage18` (mode MSX), `zzr_dracula_fireball`, `zzr_dracula_sablier_decor` et `zzzc_gfx16_screens` (mode 16 bits) est comparee
(empreinte des pixels visibles) entre la ROM avec et sans l'etape 2 : **0 image differente pendant le combat** (2 174, 526, 819 et 1 855 images ; busts 0, 1, 3, 23).
Les 65 listes de couches forcees une a une en RAM pendant le combat (`dracula+682..686`, 64 appliquees, la 65e reecrite par le script du buste dans les deux ROM) : 65 captures
identiques. Les seules differences sont transitoires (l'image suivante est de nouveau identique) : pendant les dessins de salle (une image aux portes du stage 18 ; les 12 images
du tour de dessin de la salle 9 en 16 bits, couleur de fond pendant le chargement) et des images isolees pendant les credits, ou des ecritures CPU en VRAM pendant l'affichage se dechirent a une ligne pres selon la disposition du code : une ROM temoin (sans l'etape 2, une fonction
morte ajoutee a `main.c`, comme `tests/run_playthrough_layout_md.sh`) en montre aussi (12 images a l'entree de la salle 9 en 16 bits). Les credits n'appellent pas `bust`.

## 7. Cartes en u8 puis LZ4W, `-O2` par fichier (2026-11-18)

Mesure par `make collection` (espace libre apres Vampire Killer, `VK_BASE` 0x214000), depart `01bc797`, un commit par piste :

| piste | image Vampire Killer | libre dans la collection | gain |
|-------|---------------------:|-------------------------:|-----:|
| depart (`01bc797`)                          | 0x1800EC (1 573 100) | 0x6BF14 (442 132) | |
| 1. `vk_maps` en u8                          | 0x165DEC (1 465 836) | 0x86214 (549 396) | -107 264 |
| 2. cartes `vk_maps` et `g16_*_map` en LZ4W  | 0x1443EC (1 328 108) | 0xA7C14 (687 124) | -137 728 |
| 3. `-O2` sur 5 fichiers                     | 0x13EBE8 (1 305 576) | 0xAD418 (709 656) | -22 532 |
| total                                       |                      |                   | -267 524 |

Rejeu 12-18 apres chaque piste : 55 points, 0 image perdue, 0 tour absorbe ; marge minimale 20 / 19 / 19 lignes (depart : 20 ; la limite demandee est 19).

### 7.1 `vk_maps` en u8 (-107 264 o)

Toutes les valeurs sont < 192 : `vk_maps` passe de `u16[152][704]` a `u8[152][704]` (`rooms.c/.h`, `extract_rooms.py`). Le dessin de salle MSX n'utilise plus
`VDP_setTileMapDataRectEx` mais `vk_draw_map_u8` (la boucle d'ecriture de `vk_gfx16_draw_map`, reprise telle quelle : memes ecritures VDP, memes adresses, PAL0,
`TILE_USER_INDEX`). Lecteurs : `room_view.c`, `item_view.c` (cle de l'etage 2), `gfx16.c vk_room_cell`. Gain : 107 008 o de donnees et 256 o de code.
Verification : `make test` (135 tests Python, 141 scenarios MD, tests natifs), rejeu 12-18 (marge minimale 20).

### 7.2 LZ4W des cartes de dessin (-137 728 o)

Les cartes qui ne servent qu'au dessin sont compressees une par une (`tools/lz4w_pack.py` : packer SGDK `lz4w.jar` ; le script relit chaque flux avec un decodeur Python
du `lz4w_unpack` de `tools_a.s` et refuse tout flux qui ne redonne pas les 704 octets ; decodeur essaye sur des cartes aleatoires et sur toutes les cartes du jeu) :
`vk_maps` (`vk_maps_z` + `vk_maps_off[153]`, 152 salles : 107 008 -> 38 192 o) et les cartes 16 bits `g16_*_map` (155 salles : 109 120 -> 39 608 o) ; flux alignes sur 2
(le decodeur lit par mots). La decompression a lieu au dessin de salle seulement, dans un tampon RAM de 706 o (`gfx16.c vk_map_unpack`, qui memorise la carte decompressee :
`vk_room_cell` et `vk_scene_cell`, lus cellule par cellule, ne decompressent pas deux fois la meme carte). Cout : ~19 lignes par dessin de salle (etude : 18,6 a 18,8, pire 25).
Le dessin du gel prend 2 images (budget 7) : `room_draw_vblanks` vaut 2 avant et apres (cour salle 1 et hall salle 1, `n_room_draw_margin` essaye temporairement en `== 2`), donc
la duree du gel n'a pas change ; les dessins hors gel (reapparition, debut d'etage), calibres sur l'ancienne duree, gardent le meme nombre d'images (141 scenarios, rejeu 12-18 image exacte).
Les generateurs (`build_gfx16.py`, `extract_rooms.py`) emettent maintenant les flux ; les fichiers generes ont ete convertis sur place (les 152 + 155 salles redecompressees
sont identiques aux anciennes), la ROM de reference n'etant pas dans l'arbre de travail : les generateurs modifies n'ont pas ete relances. `tests/verify_hall_map.py` et
`tools/check_gfx16_render.py` decompressent les flux. Rejeu : marge minimale 19 lignes (20 avant, meme tour f10902 : un decalage de mise en page du code, le tour n'est pas un dessin de salle).

Non fait : `late_maps` (64 512 o) et `vk_stageN_collision` (60 672 o) en LZ4W. Ces cartes sont lues a chaque image par pointeur (`vk_game_collision`, `vk_stage_room_map`, ennemis, tests natifs) :
il faudrait un tampon de salle valide pendant les passages de porte et changer tous les appelants ; ~84 Ko pour un risque de comportement et de temps qui demande une etape a part.

### 7.3 `-O2` par fichier (-22 532 o)

`sgdk/src/opt_o2.h` (`#pragma GCC optimize("O2,...")`, les options du makefile que le pragma remettrait a zero sont repetees ; sans effet dans les tests natifs) est inclus en premiere ligne de :
`msx_text.c`, `item_reveal_view.c`, `scene.c`, `stage12_secret.c` et `dracula.c`. Un `-O2` global (en-tete force sur tous les fichiers) aurait donne -109 568 o
(1 328 104 -> 1 218 536) mais est **abandonne** : rejeu 12-18 en echec (checkpoint stage 14 -> 15 manque), marge minimale 1 ligne, 2 tours absorbes.

Fichier par fichier (taille de l'image, puis rejeu 12-18 : marge minimale / 0,1 % / 1 % / mediane des tours ; reference 19 / 44 / 63 / 105) :

| essai | image | marge min / 0,1 % / 1 % / mediane | decision |
|-------|------:|-----------------------------------|----------|
| `stage_map.c`, `stage_map_view.c`, `msx_text.c`, `item_reveal_view.c`, `scene.c`, `stage12_secret.c` | 1 311 208 (-16 896) | 19 / 45 / 63 / 105 | `make test` : `zzzc_gfx16_screens` echoue (la salle n'est pas revenue 40 images apres la fermeture de la carte d'etage : `stage_map_view.c` en `-O2` ralentit la carte ; `stage_map.c` seul passe mais change le nombre d'images de ce scenario) : les deux retires |
| les 4 restants + `dracula.c` (liste finale, 5 fichiers) | 1 305 572 (-22 532) | 19 / 45 / 63 / 106 | garde (combat final, `zzp_stage18` : mediane 126 -> 125, 1 % 53 -> 52, sur ~125 lignes de marge) |
| + `wall_view.c` | 1 307 624 | rejeu image exacte en echec (checkpoint stage 13 salle 1 -> 0 manque) | refuse (comportement) |
| + `item_view.c` et `dracula_view.c` | 1 306 852 | 18 / 44 / 63 / 104 | refuse (-1 ligne ; `item_view.c` seul ne gagne que 1,4 Ko) |
| + `boss.c` (avec dracula) | 1 292 264 | 19 / 41 / 60 / 95 | refuse (mediane -10 lignes) |
| + `hud.c` | 1 290 724 | 19 / 44 / 63 / 105, mais le rejeu arrive une image plus tard (3850 au lieu de 3849) | refuse (un dessin dure une image de plus) |
| + `hud.c`, `candles.c`, `gameplay.c`, `boss.c` (avec dracula) | 1 265 124 | 12 / 35 / 55 / 89 | refuse |

Les autres fichiers chauds (`enemies.c`, `actors.c`, `player.c`, `fm_core.c`, ...) n'ont pas ete essayes un a un : les regroupements ci-dessus montrent que le gain d'octets sur la boucle de jeu
se paie en marge (mediane -10 a -16 lignes). Methode : `tools/rom_budget.py` (taille), `tests/run_playthrough_12_18_md.sh` (marge) ; pour le combat final, un script jetable lit `vk_last_slack`
a chaque tour sur `zzp_stage18`. Verification de la livraison : `make collection`, `make test` (135 Python, 141 scenarios MD, tests natifs), rejeu 12-18.

Remarque sur les scenarios : le nombre d'images de 21 scenarios sur 141 change de 1 a 6 images (et de 33 pour `zr_stage3_boss`, dont le combat depend du hasard) entre la ROM sans et avec ces cinq fichiers en `-O2`.
`dracula.c` seul donne deja 7 differences de 1 image dans des scenarios sans rapport (`f_key_door`, `zzp_stage12`...) : un decalage de mise en page du code deplace de quelques lignes le
moment ou un evenement tombe, comme pour la ROM temoin de la section 6.2 ; les `until` des scenarios absorbent ces decalages, les 141 scenarios passent et le rejeu 12-18 image exacte reste identique (3 849 images, 55 points).
