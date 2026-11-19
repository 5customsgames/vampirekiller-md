# Vampire Collection MD

Castlevania-MD et Vampire Killer MD dans une seule ROM Mega Drive de 4 Mio, sans mapper.

## Construire

Depuis la racine du dépôt :

```
make collection                  # out/vampirecollection-md.bin
make collection VK_FLAGS=-DXXX   # options de compilation de Vampire Killer seulement (CV_FLAGS pour Castlevania)
```

`collection/collection.mk` recopie `castlevania/src`, `res` et `inc` dans `build/collection/cv`, pose
par-dessus les fichiers de `collection/cv/` (`collection.c/.h` : le lancement de Vampire Killer,
`src/rom_header.c` : l'en-tête de la collection) et compile avec `collection/cv.mk` (vecteurs relais de
`sega_cv.s`, `VK_BASE` défini : l'écran SELECT GAME existe). Il recopie `vampirekiller/sgdk/src` et `res`
dans `build/collection/vk` et compile avec `collection/vk.mk` (lié à `VK_BASE`). Les ROMs seules
(`make cv`, `make vk`) n'ont ni l'un ni l'autre.

## Carte de la ROM

| Adresse              | Contenu                                                     |
|----------------------|-------------------------------------------------------------|
| `000000`             | vecteurs 68000 et en-tête de la collection                  |
| `000000`-`213FFF`    | Castlevania-MD (code lié à 0, 2,07 Mio, complété par des `FF`) |
| `214000`-`3FFFFF`    | Vampire Killer MD (lié à `VK_BASE` = `214000`, sa propre table de vecteurs SGDK), puis des `FF` |

Les deux jeux sont deux programmes SGDK complets, compilés et liés séparément : aucun conflit
de symboles ni de RAM. Chacun a toute la RAM et toute la VRAM pour lui.

## Passage d'un jeu à l'autre

- **Démarrage** : logo, puis l'écran SELECT GAME (`game_select_screen`, `castlevania/src/main.c`, compilé seulement avec `VK_BASE`).
  CASTLEVANIA continue vers ses OPTIONS ; VAMPIRE KILLER appelle `collection_launch_vk`
  (`collection/cv/src/collection.c`).
- **Lancement de Vampire Killer** : son, interruptions et affichage coupés, ports manette remis à
  0 (sinon le démarrage SGDK prend le chemin « reset logiciel » sans effacer la RAM), puis saut à
  son point d'entrée avec sa pile. Il démarre comme à la mise sous tension.
- **Interruptions** : la table de vecteurs à 0 est celle de Castlevania, mais chaque vecteur passe
  par un relais (`collection/sega_cv.s`). Le premier mot long de la RAM, `GAME_FLAG` (`FF0000`),
  est une variable initialisée des deux programmes (`collection/md_collection.ld.in`) : 0 dans
  Castlevania, `VK_BASE` dans Vampire Killer. Le relais saute au gestionnaire de Castlevania, ou
  au même vecteur de la table de Vampire Killer quand `GAME_FLAG` est non nul.
- **RESET** pendant Vampire Killer : le point d'entrée de Castlevania voit `GAME_FLAG` non nul,
  prend le démarrage à froid (RAM effacée) et revient au logo puis au choix du jeu.

`_stext` vaut `LOADADDR(.data)` dans le script de liens : la version de SGDK (`SIZEOF(.text)`)
ne marche que pour un code lié à 0.

## Limites

- 4 Mio au plus, sans mapper (cartouche flashée pour une vraie Mega Drive). Castlevania doit tenir
  sous `VK_BASE` et Vampire Killer entre `VK_BASE` et `400000` : `collection/merge_rom.py` s'arrête
  sinon, et affiche la place libre après Vampire Killer.
- L'en-tête ne déclare plus de SRAM : aucun des deux jeux ne sauvegarde, et `200000` est de la ROM.
