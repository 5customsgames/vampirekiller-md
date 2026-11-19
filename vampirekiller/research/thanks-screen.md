# Ecran de remerciements du portage (apres les credits de la fin)

Ajoute apres les credits d'origine de Dracula (`dracula.c credits()`, `dracula_view.c credits`, `generated/dracula_credits.*`, non modifies, meme minutage) :
`credits_finished` / `exit_requested` mettent maintenant `main.c` en mode `FRONT_THANKS` (`thanks.c`, `vk_thanks_begin` / `vk_thanks_tick`) au lieu d'appeler
directement `dracula_finish()` ; celui-ci est appele a la fin de l'ecran (retour a la cour avec difficulte +1 au premier passage, au titre au second :
`d->return_title`, `vk_walls.d012`, sauvegardes de l'etat de fin et `vk_dracula_view_reset()` inchanges). Contexte a part : hors rejeu 12-18 (le rejeu ne va pas jusqu'a la fin).

## Contenu et pages
Cinq pages de 330 images (la derniere 240), soit 1560 images au plus (26 s) ; START (apres 20 images) saute tout l'ecran. Textes en majuscules, 30 caracteres au plus,
police MSX (`vk_msx_font_row`) : `(C)` n'existe pas dans la police, la ligne devient `VAMPIRE KILLER BY KONAMI`.
1. THANK YOU FOR PLAYING / VAMPIRE KILLER MD / MSX2 TO MEGA DRIVE PORT ; 2. SPECIAL THANKS, DIDLITH, SHINBLAZE (avec leurs lignes) ; 3. ALL THE MEMBERS OF THE / 5CUSTOMS DISCORD SERVER ;
4. ORIGINAL GAME ... / 16-BIT ART INSPIRED BY CASTLEVANIA MEGA DRIVE ; 5. THE END.

## Decor
- 16B : le tableau de la fin de Castlevania-MD (plan B) des credits est conserve tel quel (le texte est sur le plan A, ombre noire d'un pixel pour la lisibilite).
- MSX : fond noir, cadre de deux filets de tirets.

## Texte et VRAM
64 glyphes blancs (couleur 14 de PAL0) + 64 glyphes de pseudos (couleur 13), composes un par un sur la pile depuis la police (un pixel non nul devient la couleur, ombre couleur 1 noire),
a partir de `TILE_USER_INDEX` (les 1024 tuiles du texte des credits ne servent plus ; les tuiles de l'image 16B sont apres). La carte de tuiles est ecrite en entier a chaque page.

## Raster sur les pseudos (DIDLITH, SHINBLAZE, ligne du serveur Discord)
- Degrade : une interruption HBlank (`SYS_setHIntCallback`, compteur 0 = chaque ligne) reecrit la couleur 13 de PAL0 (table `ramp[64]` en ROM, arc-en-ciel, index = ligne x 4 + 3 x image) : bandes de 16 lignes qui defilent.
  Seuls les glyphes des pseudos utilisent la couleur 13 : les autres textes restent blancs.
- Vague : HScroll en mode ligne pour le plan A (`VDP_setScrollingMode(HSCROLL_LINE, ...)`), table sinus de 72 mots en ROM (amplitude 4 pixels), ecrite chaque image sur les 8 lignes de chaque rangee de pseudo.
- Sortie (`leave()`) : HInt coupee, callback retire, mode de defilement du plan A remis par plan, HScroll A et B a 0.
- Deux pieges rencontres : (1) `DMA_transfer(CPU)` laisse l'incrementation automatique du VDP au pas (4) : `VDP_setAutoInc(2)` apres chaque ecriture ; (2) une ecriture VDP en deux mots du fil principal interrompue par
  la HInt (qui ecrit une adresse de CRAM) envoie les donnees dans la CRAM (palette corrompue, persistante) : toute ecriture VDP de l'ecran (changement de page, vague) est faite entre `SYS_disableInts` / `SYS_enableInts`,
  la HInt n'est armee qu'au tour 1, dans une section protegee.

## RAM
Aucune variable propre : le compteur d'images (2 octets) vit dans `credit_map` de `dracula_view.c` (inutilise une fois les credits finis ; `vk_dracula_view_spare()`). `tools/rom_budget.py` : marge de tas 56 o
(58 o dans la ROM de reference de `main`) ; ecart de 2 octets constate sans variable ajoutee (placement des symboles par LTO), reste largement positif.

## Verification
`tests/md_scenarios/zzzf_thanks_msx.txt` (MSX : etat de credits force par poke, pages, degrade et vague animes, START a la page 3, retour a la cour, difficulte +1) et
`zzzf_thanks_16b.txt` (16B : 5 pages jusqu'a la fin automatique en 1560 images, retour au titre au second passage) ; route commune `zzzf_thanks_route.inc`.
Captures : voir le rapport (`build`-hors depot, /tmp). Le mode `THANKS` est ajoute a `FRONT_MODES` de `tools/md_harness.py`.
