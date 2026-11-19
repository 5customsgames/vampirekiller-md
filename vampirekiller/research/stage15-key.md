# Stage 15 : la clé blanche de la salle 3 (pas de plateforme mobile)

Signalement : en salle 3, la clé blanche (32, 64) est dans une alcôve en haut à gauche, au-dessus d'un rebord de blocs, et « il manque une plateforme mobile ». Clos le 2026-11-19 : **rien ne manque, le portage est conforme à la ROM**.

## 1. La ROM n'a aucune plateforme mobile au stage 15

- Chargeur `5033` (banque 0, `LD HL,906C`) : lit des enregistrements `stage, salle, nombre, nombre x (Y, X, pas, longueur)` et compare au couple `D000` / `D001`. Table (fichier `0x506C`) : stage 5 (salle 1, salle 4 x2), stage 10 (salles 0, 2, 3, 4), puis `FF`. Aucun enregistrement pour le stage 15 ni pour un autre stage. Les autres références à `C598` (`2BB6`, `4532`) sont le transport et la sonde de Simon, pas des écritures de la table.
- La salle 3 relue en openMSX (`D100` après chargement, `tools/jump_cases_trace.tcl`) est identique à la carte du port : rebord gauche (colonnes 0 à 7, Y 80), rebord droit (colonnes 24 à 31) et vide entre les deux. Clé `84 40 20 00 18` (C500) en (32, 64), visible dès l'entrée.

## 2. Pourquoi la clé semble inatteignable depuis la salle 3

Du haut de l'escalier (Y 80, X 190), un saut fait ~30 px (mesure ROM : X 196 -> 134 en tombant au sol) ; le vide fait 120 px. Mesure ROM d'une chute verticale en salle 3 : posée sur le rebord si X <= 68, sinon elle le manque (X 69 et plus). Par les portes latérales on arrive toujours au sol de la salle 3, jamais sur le rebord.

## 3. Comment le jeu d'origine le rend accessible (vérifié ROM et port)

La salle 8 a un trou dans le sol (colonnes 12 à 15, X 96 à 127) ; la liaison « bas » de la salle 8 va à la salle 5, celle de la salle 5 à la salle 3 (liaisons `B9D3`, à sens unique).

1. Salle 8 : marcher dans le trou (le scénario de parcours le saute pour aller à la porte). Chute en salle 5 à X ~ 102 : Simon se pose sur le **bloc central de la fosse** (X 96 à 127, Y 112).
2. Marcher jusqu'à X >= 111 puis **sauter à gauche** (C + GAUCHE). Le saut est à direction fixe (pas de pilotage en l'air) ; il longe la tour gauche (mur en X 71), tombe par le fond de la salle 5 et **l'état de saut persiste dans la salle 3** : la dérive vers la gauche continue (~1 px pour 3 px de chute).
3. Salle 3 : arrivée en haut (Y 48), dérive de ~10 px jusqu'à Y 80, atterrissage sur le rebord gauche (Y 80, X 38 à 39 au mur). Marcher vers la gauche : la clé est prise au contact (X ~ 46).

Mesures ROM (openMSX, saut à gauche depuis le bloc central, salle 5, Y 112) : X de départ 100 à 110 -> sol de la salle 3 (Y 176) ; **111 à 127 -> rebord (Y 80, X 38 ou 39)**. Le port donne les mêmes valeurs (X 39 pour 111 et 127, X 38 pour 120).

## 4. Port

Aucun changement de code : table `906C` (`sgdk/src/platforms.c`), dessins MSX et 16 bits, cellules et transferts inchangés. Scénarios ajoutés (sélecteur de salle jusqu'à la salle 8, puis commandes de manette seulement) :

- `tests/md_scenarios/zzq_stage15_key_route.txt` (mode MSX) et `tests/md_scenarios/zzze_gfx16_stage15_key_route.txt` (16 bits) : 8 assertions chacun (chute 8 -> 5 sur le bloc à Y 112, saut, salle 3 en Y 80, clé prise : `items+1` bit 0). Captures : `validation/stage15-key/{msx,16bit}/`.

Ajouter une plateforme au stage 15 serait une divergence de la ROM (la table se termine après le stage 10).
