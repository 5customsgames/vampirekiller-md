# Calendrier d'affichage : du calcul d'une passe à l'écran (MSX2 et port MD)

Statut : **prouvé par trace openMSX** pour le MSX (2 exécutions, 2026-10-29) et **mesuré sur le harnais MD** pour le port, avant et après la correction. Correction **portée** : Simon, son fouet et les ennemis sont maintenant affichés deux images après le calcul, comme sur le MSX (`sgdk/src/actors.c`).

## 0. Méthode

- **Trace MSX** : `tools/run_frame_timing_trace.py ROM OUTDIR PLAN` (moteur `tools/vertical_links_trace.tcl` + `tools/frame_timing_trace_extra.tcl`), analyse `tools/analyze_frame_timing.py OUTDIR`. Openmsx 21, machine `C-BIOS_MSX2`. Plan : cour 0 → 1, `gotox 168`, fouet (ESPACE) sur la torche B, ramassage du cœur, deux fouets en l'air de parités différentes, deux sauts, hall, attente d'un contact, objet 05 posé sous Simon. Relevés : par VBLANK (crochet `4028`), `C003`, `C005`, `C006`/`C007`, X/Y, `C415`, `C417`, `C42D`, `C43E`, R#7 et la SAT entière lue en VRAM ; avec leur instant en µs depuis le VBLANK : `4BBB` (lecture des touches), `414D`, `6560`/`658A`, chaque départ de commande VDP (écriture de R#46 par le port 9Bh, avec DX, DY, NX, NY), `CHGCLR` (`0062`), les demandes de son `509F` et les écritures de `C096`, `C415`, `C417`, `C42D`. Sorties brutes hors dépôt (`scratchpad/ft/out1`, `out2` de la session).
- **Conventions MSX** : image N = image balayée après le VBLANK N. Une écriture VRAM faite t µs après le VBLANK N, sur la ligne y (212 lignes affichées sur 262), est dans l'image N si t < (50 + y) × 63,7 µs, sinon dans l'image N + 1 (calcul, non vérifié au pixel : les cas relevés sont loin de la limite, sauf la case du HUD). La SAT lue au VBLANK N + 1 est celle de l'image N. Un son demandé pendant l'image N part au VBLANK N + 1 (`8964` tourne au début de chaque interruption, `403B`, avant le garde `C005`).
- **Port** : `python3 tools/measure_md_frame_timing.py --out DIR` (harnais `md_harness.py`, Genesis Plus GX). Dans ce core, un `retro_run` commence par la V-Int puis balaie l'image : l'image du run r est l'image après la V-Int r ; le tour de boucle de `main.c` qui suit la V-Int r (« itération r ») a lu la manette de cette V-Int (`JOY_update`). Mesuré : un bouton tenu au run r0 change la RAM à l'itération r0 (fouet : `whip.timer` = 14 et son 05 demandés au run r0 ; marche : X + 1 au run r0).
- **Correspondance** : l'itération r du port correspond à la passe qui commence au VBLANK p du MSX. Vérifié sur la RAM : le port et le MSX changent X (marche), `C422`/`whip.timer` et le son du fouet dans la passe qui lit la touche, Y au 4e image (saut, `jump-compare.md`), la silhouette de 09/08 à la passe suivante.

## 1. MSX : où et quand chaque élément est produit

Une passe de jeu (`C003` + 1) dure 2 images : `4028` appelle `8964` (son) à chaque VBLANK, puis, si `C005` est libre, `4B9D` (touches) et `414D` (passe). La passe dépasse le VBLANK suivant (`C005` = 1 au VBLANK du milieu, la passe se termine dans la 2e image) ; les passes de chargement de salle durent 18 à 37 images.

| Élément | Tampon / écriture | Moment dans la passe p (trace) | Image à l'écran |
|---|---|---|---|
| Touches | `4BBB` lit la ligne 8 et le port joystick (`C007` tenues, `C006` nouvelles) | 0,5 à 2,6 ms après le VBLANK p (médiane 0,6 ms), seulement aux débuts de passe | — |
| Sprites (Simon, fouet, ennemis, flamme qui tombe d'une torche) | `D600` (Y par `78CC`, ~13 ms), `D400` (`790C`) ; envoyés par `6560`/`658A` au début de la passe suivante | envoi à 0,8-2,9 ms du VBLANK p + 2 | **p + 2** (et p + 3) |
| Décor en bitmap : torche éteinte, cœur posé ou ramassé, bloc | commandes VDP `HMMM` (D0h) sur la page 0, au moment du calcul | torche : VBLANK p + 1 + 4,9 ms (lignes 144-159) ; cœur ramassé : p + 1 + 1,5 ms | **p + 1** |
| HUD : barre ENEMY/PLAYER, cœurs, case d'objets, clé | commandes VDP (`C0`/`70`/`D0`) sur les lignes 0 à 31 | barre : p + 15,6 ms puis p + 1 + 0,7 à 4,3 ms ; cœurs : p + 1 + 5,7 ms ; case : p + 1 + 3,0 ms | **p + 1** (dernières commandes : p + 2) |
| Animation des flammes (torches, bougies) | `LMMM` (98h) | à chaque passe | p ou p + 1 |
| Bordure (objet 05, `7604`) | `CHGCLR` écrit R#7 tout de suite | p + 8,2 à 9,0 ms | **p à partir de la ligne ~80, p + 1 entière** |
| Son | `509F` (demande), `C096` ; `8964` au VBLANK suivant | fouet 05 : p + 8 à 9 ms ; coup 0C : p + 1 + 3,3 ms ; cœur 0F : p + 1 + 6,1 ms ; 1B (05) : p + 1 + 12,8 ms ; dégât 13 : p + 7,5 ms | **p + 1** (demande dans la 1re image) ou **p + 2** (dans la 2e) |

Entrées mesurées (touche enfoncée au VBLANK k0) : la lecture tombe à k0 si k0 commence une passe, sinon à k0 + 1 ; la première image où la SAT change (entrées triées : `6560` tourne leur ordre à chaque passe, `C00F`) est la lecture + 2 :

| Action | k0 | Lecture (p0) | 1re image changée | Retard depuis k0 |
|---|---|---|---|---|
| Fouet (cour 1) | 1186 | 1187 | 1189 | +3 |
| Marche droite | 1288 | 1289 | 1291 | +3 |
| Fouet en l'air | 1373 | 1373 | 1375 | +2 |
| Fouet en l'air | 1416 | 1417 | 1419 | +3 |
| Saut | 1478 | 1479 | 1485 (Y à p0 + 4) | +7 |
| Saut | 1561 | 1561 | 1567 | +6 |

Fouet sur la torche B (passe p0 = 1187) : son 05 au VBLANK 1188 (p0 + 1), première pose 1189 (p0 + 2), contact dans la passe 1189 : torche effacée dans l'image 1190, son 0C au VBLANK 1191 et pose du contact dans l'image 1191. La torche disparaît donc une image avant que la pose qui la touche soit affichée.

Contact (hall) : `4638` baisse `C415` à la passe 2239 (barre du HUD dans l'image 2240) ; `6F9F` pose `C42D` et demande le son 13h à la passe suivante 2241 (son au VBLANK 2242, Simon caché dans l'image 2243).

## 2. Port : où et quand chaque élément est produit

| Élément | Écriture | Image (itération r) |
|---|---|---|
| Manette | `JOY_update` à chaque V-Int, lue par l'itération qui suit | chaque image (le MSX : une sur deux ; gardé, section 4) |
| Sprites | `VDP_updateSprites(..., DMA_QUEUE)`, envoi à la V-Int r + 1 | r + 1 (avant correction pour tous) |
| Tuiles sous le HUD : support des torches, blocs cachés, bougies de la salle 0, clé blanche et porte | `VDP_setTileMapDataRow(..., DMA_QUEUE_COPY)`, envoi à la V-Int r + 1 (avant : `VDP_setTileMapXY` au CPU, image r) | r + 1 (mesuré : A+B rallume la torche A, cellules et flamme-sprite à r + 1) |
| Message de la ligne 26 (debug) | texte au CPU | r |
| HUD (barre, chiffres) | tuiles au CPU, lignes 0 à 31 déjà balayées | r + 1 (mesuré : contact, barre à r + 1) |
| Couleur de fond (objet 05) | `vk_show_backdrop` juste après la V-Int r + 1 | r + 1 entière |
| Son | `vk_psg_effect`, lecteur en V-Int | V-Int r + 1 |
| Bougies, objets lâchés, case d'objets, clé du HUD, flammes des torches (bitmap sur MSX) | sprites (`candle_view.c`, `room_view.c`) | r + 1 |

## 3. Comparaison et décision

Retards depuis le début de la passe (MSX p) ou l'itération (port r) qui calcule l'élément :

| Élément | MSX | Port avant | Port après |
|---|---|---|---|
| Simon, fouet, ennemis (sprites MSX) | p + 2 | r + 1 | **r + 2** |
| Bougies, objets lâchés, case et clé du HUD, flammes des torches (bitmap MSX, sprites MD) | p + 1 | r + 1 | r + 1 |
| Décor sous le HUD (tuiles MD) | p + 1 (p si dessiné tôt dans la 1re image) | r | **r + 1** |
| HUD (barre, chiffres) | p + 1 (parfois p + 2) | r + 1 | r + 1 |
| Bordure / fond (05) | p (dès la ligne ~80), p + 1 entière | r + 1 | r + 1 |
| Son | p + 1 ou p + 2 selon le moment de la demande | r + 1 | r + 1 |
| Touche → 1re image de Simon changée | +2 ou +3 (lecture une image sur deux) | +1 | **+2** |

Avant la correction, seuls les sprites MSX étaient en avance d'une image sur tout le reste : Simon caché ou en silhouette une image avant la barre du HUD et le son, pose du fouet affichée en même temps que son son (MSX : une image après), objet 05 qui allume le fond en même temps que les sprites au lieu d'une image avant. Le retard global (touche → image) était aussi plus court d'une à deux images.

**Implémenté** (`actors.c`, `vk_show_player`) : la table envoyée à la V-Int r + 1 porte, pour les sprites 0 à 6 (Simon, fouet) et les ennemis, les entrées construites au tour précédent (`swap_entries`), avec les tuiles du bouclier et la couleur de silhouette (PAL3 1-3) qu'elles demandent, chargées par la même file DMA. Les sprites qui sont du bitmap sur le MSX (bougies, objets, HUD, flammes des torches) restent à une image. `vk_actors_flush` (appelé par `hide_sprites` de `main.c` et par `vk_load_whip_graphics`, à chaque chargement de scène) vide le tampon : après le gel d'un changement de salle, Simon et les ennemis réapparaissent deux images après la première passe, comme quand le MSX vide sa SAT (`47F0`, `63C5`). Coût : 37 entrées de 8 octets copiées par image, aucune image de plus pour la manette au-delà de celle du MSX (+2, contre +2 ou +3 sur le MSX).

Mesures du port après correction (`tools/measure_md_frame_timing.py`) : fouet et marche, 1re image changée à r0 + 2 (avant : r0 + 1) ; son du fouet à la V-Int r0 + 1 ; cellules de la torche à r (r + 1 depuis le passage par la file DMA, ci-dessous), flamme à r + 1 ; barre du HUD au contact à r + 1 ; fond de l'objet 05 à la passe + 4 en RAM, image + 1. Scénario `w_simon_blink_phase` : silhouette affichée aux images +4 à +301 (passe paire) et +6 à +299 (impaire) depuis le début de la passe du ramassage, exactement les images de la trace MSX (`castle-candles.md` 9.8 ; avant : une image plus tôt).

**Décor sous le HUD, corrigé** (2026-10-29) : les tuiles du décor (`room_view.c` `set_courtyard_flame_background`, `candle_view.c` `draw_hidden_block` et `vk_candle_view_out`, `item_view.c` `draw_block` pour la clé blanche, la porte et la case du HUD) passent par la file DMA (`DMA_QUEUE_COPY`, une ligne de cellules par entrée) et changent à r + 1, comme le décor MSX (p + 1) et les sprites des bougies. Les tuiles des objets lâchés (`load_object`) sont aussi chargées par la file, avec la table des sprites qui les montre. L'ordre des écritures est gardé : la clé dessinée sur un bloc qui vient d'être cassé passe après lui dans la file (sinon la cellule du bloc, envoyée à la V-Int, effaçait la clé : scénario `x`). Mesure (`tools/measure_md_frame_timing.py`, avant et après) : A+B, torche A rallumée à l'itération r : avant, cellules du support à r (178 pixels non noirs) et flamme à r + 1 ; après, rien à r, cellules et flamme ensemble à r + 1. Au fouet, l'étincelle de l'objet lâché (sprite) recouvre le support et masque la mesure ; la règle est la même (écriture dans l'itération de la passe, image suivante), donc la torche éteinte paraît une image avant la pose qui la touche, comme sur le MSX (image 1190 contre pose 1191). Scénario `zf_decor_next_frame` (image r inchangée, image r + 1 changée).

## 4. Écarts restants (non corrigés)

- **Sons** : le port envoie tout son à r + 1 ; le MSX à p + 2 quand la demande tombe dans la 2e image de la passe (coup 0C `7FD8`, ramassage `8D3E`, 1B de 05). Le son du coup part donc une image avant la pose du contact (MSX : ensemble). Écart d'une image (17 ms), non corrigé.
- **Lecture de la manette, gardée à chaque image (décision du 2026-10-30)**. MSX (code) : `4B9D` n'est appelé qu'au début d'une passe ; `4BBB` lit l'état instantané de la ligne 8 et du joystick, `4BB4` range les touches tenues dans `C007` et les nouvelles (`(ancien XOR nouveau) AND nouveau`) dans `C006`. Un appui qui commence et finit entre deux lectures (moins de 2 images, selon la phase) n'existe pas pour le jeu : un appui d'une image est perdu une fois sur deux, un appui de 2 images ou plus est toujours vu. Retard touche → écran : +2 ou +3 (moyenne 2,5) ; port : +2 (mesuré). Le port lit `JOY_update` à chaque V-Int et sa logique avance à chaque image (marche de 1 px par image, minuteries du fouet, saut dont la courbe est calée sur l'appui) ; il n'a pas la structure en passes de 2 images. Lire une image sur deux ne rapprocherait que la perte des appuis d'une image et la demi-image de retard en plus, sans autre effet visible : un appui humain dure en pratique 3 à 6 images (50 à 100 ms), toujours vu des deux côtés, et le calendrier d'affichage (Simon à r + 2) est déjà celui du MSX à la meilleure phase. Reproduire la lecture rendrait le jeu un peu moins réactif (appuis brefs perdus au hasard) pour un écart d'une image au plus : **non reproduit**. À revoir seulement si une mécanique dépendait de la parité de la passe au moment de l'appui (aucune trouvée : la phase du clignotement suit `C003`, déjà porté par `itemPhase`/`tick`).
- **Contact** : le MSX baisse l'énergie (`4638`) une passe avant de poser `C42D` et le son 13h (`6F9F`) ; le port fait les trois dans la même itération. Logique de jeu, hors de ce calendrier.
- **Bordure** : le MSX change R#7 au milieu de l'image p (vers la ligne 80) : la première image est coupée en deux. Le port change tout le fond à r + 1.
- **Ligne de partage** des écritures VRAM du MSX calculée (50 lignes avant la ligne 0, 63,7 µs par ligne), non vérifiée au pixel (pas de capture d'écran sans rendu OpenGL).

## 5. Marge des tours de jeu (`vk_last_slack`) : plancher de 6 lignes, rejeu 12-18 (2026-11-16)

Règle : un tour de boucle ordinaire doit finir au moins **6 lignes** avant le VBlank suivant (`SLACK_FLOOR` de `tools/playthrough_12_18_md.py`).
Le rejeu image exacte (`tests/run_playthrough_12_18_md.sh`) en signalait 54 sous le plancher, sans image perdue ni tour absorbé :
27 en stage 12 salle 6 (images 4 611 à 4 637, minimum -9) et 27 en stage 15 salle 9 (images 26 327 à 26 353, minimum -10).

**Cause : une erreur de mesure, pas un tour coûteux.** Ces 54 tours sont les images noires qui suivent la mort des boss 12 et 15
(`stage_blank`, `BOSS_EXIT_FRAMES`, main.c) : le tour ne fait presque rien (5 à 8 lignes, mesuré sur la ROM `VK_PROFILE` : marque 0 à
la ligne 233, marque 31 à la ligne 234). Il commence juste après la V-Int (ligne ~230) et finit **dans le même VBlank**. `vk_turn_sync`
lisait alors « dans un VBlank, aucun VBlank commencé pendant le tour » comme un tour fini *après* le début du VBlank (224 - ligne, soit -6
à -10), alors que l'échéance est le VBlank suivant, une image plus loin. Correction (`vk_turn_sync`, main.c) : sans VBlank traversé et
dans le VBlank à la ligne >= 224, la marge est 224 + (262 - ligne) (~256). Le cas ne peut pas cacher un vrai dépassement : les interruptions
sont ouvertes dans `vk_turn_sync`, une V-Int en attente du VBlank suivant aurait déjà incrémenté `vtimer` (le tour serait compté `crossed`).
La correction ne touche qu'une variable de mesure (aucune logique de jeu).

**Vrai coût réduit en même temps : la barre du HUD aux coups sur un boss.** Les tours ordinaires les plus chargés des salles de boss
(ROM `VK_PROFILE`, boss 15 : ~250 lignes, 7 tours absorbés) passaient 76 à 80 lignes dans `vk_hud_update` : à chaque coup sur le boss la
barre ENEMY change et `build_bar` (hud.c) recalculait les 27 tuiles (216 mots, ~100 cycles chacun). Désormais une colonne n'est recalculée
que si ses masques (`cut`, `ecut`) ont changé depuis la dernière construction (un coup déplace une ou deux colonnes) ; `bar_tiles` est
identique à une construction complète et la file DMA envoie toujours les 27 tuiles. Un dessin du HUD (`vk_hud_show`, dessin de salle)
garde la reconstruction complète : les dessins hors gel (début de stage, porte du boss) comptent comme des pas de jeu calés sur leur durée
(`room-draw-budget.md`) ; essayé sans cette garde, le dessin du début du stage 13 raccourcissait et le rejeu divergeait (salle 13.1 au lieu de 13.0).

Mesures (ROM normale, mode PSG + graphismes MSX = celui du rejeu ; outil : rapport du rejeu, lignes de 489 cycles) :

| | avant | après |
|---|---:|---:|
| tours ordinaires | 28 811 | 28 811 (même suite image / stage / salle) |
| marge minimale | -10 | **19** (stage 15 salle 2, image 10 902) |
| tours sous 6 lignes | 54 | **0** |
| 0,1 % / 1 % / médiane | -6 / 59 / 106 | 44 / 63 / 105 |
| salle 12.6 (boss 12), hors images noires | 37 | 80 |
| salle 15.9 (boss 15), hors images noires | 22 | 44 |
| points de contrôle | 55 | 55, mêmes images (CRC de chaque image affichée : 29 860 images, seules 35 diffèrent, toutes pendant un dessin de salle qui finit quelques lignes plus tard) |

Salles les plus serrées après correction : 15.2 (19), 15.1 (23), 14.4 (28), 14.6 (33). Les 54 tours des images noires : 253 à 256 lignes.
Coût de `vk_hud_update` (ROM `VK_PROFILE`, stages 12-13) : moyenne 1,3 ligne, maximum 80 avant, 20 après. Coût des tours de 15.1 / 15.2 (ROM de mesure) :
`show_player` ~107 lignes dont sprites des ennemis 75 (`Enemies_sat_render` 21, `Enemies_sprites` 38), ennemis 90 (IA 45) : beaucoup
d'aigles et de puces, de la logique de jeu, non touchée.

**Autres modes** (mis à jour au 2026-11-19 : cause trouvée, rejeu en FM et en 16 bits rendu possible, marge mesurée, voir la section 6). Le rejeu n'est enregistré qu'en PSG + graphismes MSX : en FM ou en 16 bits (touches du titre, `VK_SOUND_FM=1` ou le
nouveau `VK_GFX16=1` du rejeu), il diverge au début du stage 14 (avant comme après ce correctif) : le dessin du début de stage, calé sur sa
durée, prend une autre image avec la V-Int FM ou les tuiles 16 bits. Sur les stages 12 à 14 (3 453 tours alignés) : FM, marge minimale 25 ;
16 bits, 36 ; FM + 16 bits, 23. Écart par tour avec le PSG : FM de -2 à +24 lignes (médiane 6, 99 % : 19 ; le pas FM est dans la V-Int,
avant le début du tour) ; 16 bits de -5 à +5. Pour le stage 15 en FM, mesure de borne haute : rejeu PSG, puis à l'image d'entrée du stage 15
+ D (D = 40 à 240, 9 phases de la musique) la V-Int passe sur `fm_vint` et le flux FM de la musique du stage démarre par écriture RAM
(script de mesure non versionné, le PSG garde ses 3 voix : coût supérieur au vrai mode FM) ; le rejeu passe en entier à chaque fois.
Marge minimale **8** (15.2, image 10 902, deux phases sur neuf), 12 à 31 sinon ; 15.9 : 31 à 36. Le plancher tient, mais 15.2 est le point
le plus fin en FM : un pas FM maximal (~24 lignes de plus que le PSG) sur le tour de 19 lignes passerait sous 6. Levier suivant si besoin :
`Enemies_sprites` des tirs est calculé deux fois par tour (`Enemies_sat_render` puis `show_enemy_sprites`).

Remarque : la ROM de mesure `VK_PROFILE` de ce correctif diverge au début du stage 13 (le dessin du début de stage, calé sur sa durée, y finit
une image plus tôt : tous ses dessins sont ~75 lignes plus courts que ceux de la ROM de mesure sans le correctif de hud.c, dès le premier gel,
avant tout coup sur un boss ; non élucidé à l'époque, **non reproduit au 2026-11-19, voir la section 6.3**). La ROM normale et les deux variantes de `tests/run_playthrough_layout_md.sh` passent, avec des
dessins à 3-10 lignes de ceux d'avant. Ce dessin finit 34 à 52 lignes après le début de son VBlank selon la ROM : s'il raccourcissait de
plus que ça, le rejeu divergerait (fragilité antérieure, à garder en tête).

Outils : `tools/playthrough_12_18_md.py` imprime maintenant les tours sous le plancher par salle et les salles les plus serrées ;
`--min-slack N` fait échouer le rejeu sous N lignes ; `tests/run_playthrough_12_18_md.sh` le passe avec 6 par défaut (`MIN_SLACK=` pour l'enlever).
Profil par étape : ROM `make -C vampirekiller/sgdk GDK=... EXTRA_FLAGS=-DVK_PROFILE` (marques `VK_MARK`, plus lente d'environ 20 lignes par tour) ; **partir d'un `rm -rf vampirekiller/sgdk/out`** (le `make` ne suit pas les `-D`, section 6.3).

## 6. Deux désynchronisations du rejeu 12-18 élucidées, marge en FM + 16 bits, RAM au démarrage (2026-11-19)

Méthode : traces image par image du rejeu (stage, salle, position de Simon, `vk_turns`, `vtimer`, `vk_draws`, `vk_last_slack`) alignées sur le point de contrôle, en PSG + MSX, FM, 16 bits et avec la ROM `VK_PROFILE` ;
durée d'un dessin = (VBlanks du tour) x 262 - marge lue en fin de tour. Aucune modification du jeu : le jeu MSX, le rejeu standard (55 points, 0 image perdue, 0 absorbée, marge minimale 19, mêmes 28 811 tours)
et la ROM normale (identique octet pour octet, vérifié) sont inchangés.

### 6.1 Rejeu en FM ou en 16 bits : désynchronisation légitime (durée du dessin), pas un bug

Reproduit : FM échoue à l'image 7549, 16 bits à 7551 (stage 14, « stage 14 salle 3 attendu »). Jusque-là les deux modes suivent la même route (décalage constant de 8 images dû aux touches du titre, mêmes points de contrôle).
Zéro image perdue, zéro tour absorbé : ni dépassement d'image ni aléa (le rejeu est déterministe).

Cause : le dessin du début de stage n'est pas un gel : il compte pour un pas de jeu calé sur sa durée (`room-draw-budget.md`). Son tour de boucle finit L lignes après le début d'un VBlank ; le tour suivant (le premier pas de jeu)
commence au VBlank d'après. Si le dessin s'allonge de plus de 262 - L lignes, les pas de jeu arrivent une image plus tard et chaque entrée, enregistrée image par image, tombe une image trop tôt sur les pas de jeu
(Simon part à l'image 7347 en PSG, 7356 en FM : 8 + 1 images). Mesure (lignes ; le rapport du rejeu les imprime, ligne « draws that are not freezes ») :

| dessin | PSG + MSX | FM | 16 bits | ROM VK_PROFILE |
|---|---:|---:|---:|---:|
| début du stage 13 : durée / fin après le début d'un VBlank | 2 683 / 63 | 2 662 / 42 | 2 798 / 178 | 2 685 / 65 |
| début du stage 14 : durée / fin après le début d'un VBlank | 2 567 / **209** | 2 629 / 9 (VBlank suivant) | 2 754 / 134 (VBlank suivant) | 2 568 / 210 |

Le dessin du stage 14 finit à 209 lignes : il ne lui reste que **53 lignes** avant l'image suivante. La V-Int FM ajoute ~7,7 lignes par image (+62 sur les ~8 images du dessin) et les chargements de tuiles 16 bits +187 :
les deux dépassent 53 lignes, d'où une image de retard dès le stage 14. Le stage 13 a 199 lignes de tolérance en plus : il passe en FM seul ou en 16 bits seul ; en FM + 16 bits il est déjà en retard (divergence à l'image 5193).

Pas de correctif du jeu sûr : faire attendre le dessin MSX / PSG jusqu'à la même image décalerait le jeu MSX d'une image (les scénarios sont calés sur cette durée) ; raccourcir le dessin FM / 16 bits de 62 à 187+ lignes
demanderait un autre chemin de dessin. C'est le **rejeu** qui s'adapte : `tools/playthrough_12_18_md.py` insère une image sans touche (`H 1 -`) après le début de chaque stage dont le dessin prend une image de plus
(`shifted()`, `MODE_SHIFTS`, option `--stage-shift`, choisi d'après `VK_SOUND_FM` / `VK_GFX16`) : FM : stage 14 ; 16 bits : 14 et 15 ; FM + 16 bits : 13, 14 et 15. Le jeu refait alors le même parcours avec le calendrier du mode.
`tests/run_playthrough_modes_md.sh` lance les trois variantes avec le plancher de 6 lignes.

### 6.2 Marge minimale en FM, 16 bits et FM + 16 bits (mesure complète)

Rejeu entier de 12 à 18, 55 points, 0 image perdue, 0 tour absorbé, 0 tour sous 6 lignes dans chaque mode :

| mode | tours | marge min | plus serrées |
|---|---:|---:|---|
| PSG + MSX (référence) | 28 811 | **19** | 15.2 19, 15.1 24, 14.4 29 |
| FM | 28 811 | **12** | 15.2 12, 15.1 21, 13.5 23, 14.4 23 |
| 16 bits | 28 804 | **9** | 16.0 9 (le tour qui suit le dessin du début du stage 16), 15.2 19, 15.1 22 |
| FM + 16 bits | 28 802 | **11** | 15.2 11, 15.1 14, 14.4 22, 13.5 23 |

La salle 15.2 reste le point le plus serré (19, 12, 11 lignes) ; la borne de 8 lignes de la section 5 (V-Int FM lancée par écriture RAM, sans rejeu complet) était un peu pessimiste. Le plancher de 6 lignes tient dans les quatre modes,
avec 3 lignes de marge au plus juste (16 bits, salle 16.0). Le levier cité (`Enemies_sprites` calculé deux fois par tour : `Enemies_sat_render` pour les tirs actifs et le dragon, puis `show_enemy_sprites` pour tous) n'est pas utilisé :
`Enemies_sat_render` fait évoluer `sat_used` en cours de boucle et la liste du boss 15 (`boss15_sat`) en dépend, rien ne prouve que le second appel redonne la même liste, et ces marges ne l'exigent pas.

### 6.3 ROM `VK_PROFILE` : non reproduit ; elle ne démarrait plus (RAM)

Construite telle quelle au point de départ de cette étude, la ROM de mesure ne démarre pas : écran noir, `vtimer` à 0. Le compteur de programme (état de sauvegarde du core) est dans la boucle d'erreur de SGDK « Not enough memory to reset VDP ! » :
**`VDP_resetScreen`, appelé par `SYS_init` avant `main()`, alloue d'un bloc la police par défaut (3 082 o avec son en-tête)**, après la file DMA (1 282 o) et le tampon de données DMA (8 194 o) ; le tas (de `_bend` à 0xFFF600) fait 12 616 o :
**58 o de marge** seulement. Un tableau factice de 48 o dans le jeu normal démarre, de 64 o non ; les deux tables de marques de `VK_PROFILE` (2 x 56 x 4 o = 448 o) dépassent donc la limite. Rien à voir avec la taille de la ROM
(une ROM de 1,375 Mio démarre). Toute variable ajoutée au jeu normal au-delà de 58 o a le même effet, et rien ne le signalait. Corrections :
- `tools/rom_budget.py` imprime la marge de RAM au démarrage et `--check` échoue au-dessous de 0 (`tests/run_rom_budget.sh`) ;
- `credit_map` (2 Kio, texte du générique de fin) est réduit à 64 cases, index masqué, **dans la ROM `VK_PROFILE` seulement** (`dracula_view.c`) : marge de 1 526 o ; le générique y est brouillé (non mesuré). La ROM normale est inchangée.

Levier non appliqué : le tampon DMA de SGDK (8 192 o par défaut, `DMA_BUFFER_SIZE_NTSC` dans `libmd.a`, commune à Castlevania-MD et à ce jeu) n'est utilisé qu'à hauteur de **150 o au plus** dans le rejeu 12-18 (file : 26 entrées sur 80 ; compteurs
temporaires dans `DMA_allocateTemp` / `DMA_queueDma`, retirés). Le réduire rendrait ~6 Kio de RAM, mais il demande l'accord des deux jeux et une mesure de tous les scénarios, et sa taille est fixée avant `main()` : non fait.

Avec une ROM de mesure qui démarre, construite proprement : **le rejeu standard passe, 55 points**, et les dessins de début de stage sont à 1 ou 2 lignes de ceux de la ROM normale (tableau ci-dessus), pas « ~75 lignes plus courts » (section 5).
Cette différence expliquerait bien le symptôme noté : le dessin du stage 13 finit 63 lignes après le début d'un VBlank, un dessin plus court de plus de 63 lignes finit une image plus tôt. Cause la plus probable, non prouvée : une ROM de mesure faite avec
des objets périmés ou un état intermédiaire de `hud.c` : **le `make` ne suit pas les `-D`**, changer `VK_FLAGS` sans `rm -rf vampirekiller/sgdk/out` mélange les objets (j'ai moi-même obtenu à tort une « ROM de mesure » ainsi pendant l'étude : marges identiques
à celles de la ROM normale, ce qui la trahit). Le dessin du HUD (`vk_hud_show`, `built_valid = FALSE`, hud.c) reconstruit bien toutes les colonnes dans le code actuel.

Tolérances des dessins hors gel (rapport du rejeu, PSG + MSX : plus court de / plus long de) : stage 14 : 209 / **53**, stage 13 : 63 / 199, porte du boss 15 : 61 / 201, stage 17 : 96 / 166, stage 15 : 97 / 165.
C'est le point fragile de ce rejeu : un changement qui modifie le coût d'un dessin de début de stage de plus que sa tolérance décale tout le rejeu d'une image ; il est annoncé par un point de contrôle manqué, non par une image perdue.
