# VampireCollectionNextGen

> **Projet de fan, non officiel et sans but commercial.** *Castlevania* et *Vampire Killer* sont des
> marques et œuvres de Konami. Ce dépôt ne contient pas les ROM d'origine (NES, MSX2) : les données
> de jeu qui en sont extraites (graphismes, cartes, sons) sont incluses sous forme générée pour que
> le build soit autonome. Si un ayant droit en demande le retrait, le dépôt sera supprimé.

## Obtenir les ROM

Aucune ROM n'est distribuée ici : elles se construisent depuis les sources avec `make` (voir « Construire »
plus bas), sans avoir besoin des ROM d'origine. Le résultat, dans `out/`, est `vampirecollection-md.bin`
(les deux jeux, écran SELECT GAME, 4 Mio sans mapper), `castlevania-md.bin` et `vampirekiller-md.bin`.
Elles tournent sur émulateur (Genesis Plus GX, BlastEm…) et sur console avec une flash cartridge.

## Vampire Killer MD en bref

Portage complet de *Vampire Killer* (MSX2) : 18 stages, tous les boss, Dracula, la fin. Deux modes
graphiques au choix sur l'écran titre : **MSX** (aspect d'origine) et **GRAPH 16B** (tout redessiné
dans le style de Castlevania MD, même gameplay). Son PSG ou FM, test sonore, écran de remerciements.

## Licences et droits

- **Code du portage** : licence MIT (`LICENSE` à la racine, copies dans `castlevania/` et `vampirekiller/`),
  y compris `collection/`. `sgdk/` est SGDK (Stephane Dallongeville), sous sa propre licence
  (`sgdk/license.txt`, `sgdk/COPYING.RUNTIME`).
- **Ces licences ne couvrent que le code et les outils écrits pour ce projet.** Les graphismes, cartes,
  musiques et sons dérivés de *Castlevania* (NES) et de *Vampire Killer* (MSX2), présents sous forme
  générée dans `*/src/generated/`, `castlevania/res/` et les ROM construites, restent la propriété de
  **Konami** : ils ne sont pas sous licence MIT.
- Les ROM d'origine (NES, MSX2) ne sont pas fournies, et aucune ROM construite n'est publiée ici : elles ne doivent pas être déposées dans ce dépôt (voir `.gitignore`).
- Retrait : toute demande d'un ayant droit sera honorée, le dépôt sera supprimé.

## Remerciements

Merci à **Didlith** pour ses nombreuses soirées de tests, à **Shinblaze** pour les validations sur
console physique, et à tous les membres du serveur Discord **5Customs**.

Les deux portages Mega Drive de 5Customs et leur compilation, dans un seul dépôt autonome :

| Dossier | Contenu | ROM |
|---|---|---|
| `castlevania/` | Castlevania-MD (NES → Mega Drive), ex-dépôt `castlevania-md` | `out/castlevania-md.bin` |
| `vampirekiller/` | Vampire Killer MD (MSX2 → Mega Drive), ex-dépôt `vampirekiller-MD` | `out/vampirekiller-md.bin` | 
| `collection/` | Vampire Collection MD : les deux jeux dans une ROM de 4 Mio sans mapper, ex-dépôt `vampirecollection-md` | `out/vampirecollection-md.bin` |
| `sgdk/` | SGDK (version `ee6870a`) avec le correctif GCC 16, sans les binaires Windows | — |

L'historique Git des trois anciens dépôts est conservé, chacun dans son dossier
(`git log castlevania/src/main.c` remonte au premier commit de Castlevania-MD).

## Prérequis

Sur la machine : `m68k-elf-gcc` et ses binutils (testé avec GCC 16.1), un compilateur C/C++ (pour
`sjasm` et `bintos`, compilés depuis `sgdk/tools`), Java (outils SGDK), Python 3, `rsync`. Pour les
tests : le cœur libretro Genesis Plus GX (`/usr/lib/libretro/genesis_plus_gx_libretro.so`) et la ROM
MSX de référence de Vampire Killer (non fournie : à placer dans `vampirekiller/` sous le nom `Vampire Killer (Japan, Europe) (En).zip`) ; sans elle, `make vk collection` fonctionne, seuls les tests et la régénération des données en ont besoin.

## Construire

```sh
make              # les trois ROMs dans out/
make cv           # Castlevania-MD seul
make vk           # Vampire Killer MD seul
make collection   # la collection ; affiche la place libre restante sous 4 Mio
make vk VK_FLAGS=-DGOD_MODE    # options de compilation d'un jeu (CV_FLAGS pour Castlevania)
make clean
```

La première compilation construit SGDK (`sgdk/lib/libmd.a`) et ses outils Z80. Les produits de
compilation vont dans `build/`, `out/` et les dossiers `out/` de chaque jeu, jamais versionnés.

La ROM de Vampire Killer seule n'a pas de limite de taille. Celle de la collection doit tenir dans
4 Mio : si Vampire Killer dépasse, seule `make collection` échoue, avec la taille en trop
(`collection/merge_rom.py`).

## Tester

```sh
make venv         # .venv avec les paquets de requirements.txt
make test         # Vampire Killer : tests natifs, tests Python, scénarios Mega Drive (en parallèle)
```

Les journaux des scénarios sont dans `build/scenarios/`.

## Organisation des jeux

Les deux jeux restent deux programmes SGDK séparés, chacun avec toute la RAM et la VRAM. Le code de
la collection (écran SELECT GAME, lancement de Vampire Killer, vecteurs relais) n'est compilé que dans
la collection : voir `collection/README.md`.
