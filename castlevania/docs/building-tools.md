# Outils et régénération des données

Ce projet repose sur une suite d'outils Python permettant d'extraire et de convertir les données d'une ROM NES originale (*Castlevania USA Rev 1*) et d'un checkout du portage SNES.

---

## Configuration de l'environnement Python

L'exécution des scripts nécessite Python 3 et la bibliothèque `py65` :

```bash
pip install py65
```

---

## Chaîne de régénération complète

Les données 16-bit proviennent du dépôt `castlevania-snes`. Une fois importées dans `tools/extracted/snes`, le dépôt externe n'est plus nécessaire.

```bash
# 1. Importation des assets SNES
python3 tools/import_snes.py ../castlevania-snes

# 2. Extraction du binaire et des tuiles NES
python3 tools/extract_chr.py rom.nes

# 3. Enregistrement des séquences et décodage
python3 tools/record_level.py rom.nes
python3 tools/record_rooms.py rom.nes
python3 tools/record_candles.py rom.nes
python3 tools/record_simon.py rom.nes
python3 tools/record_screens.py

# 4. Conversion vers le code source C du projet MD
python3 tools/level_to_md.py
python3 tools/screens_to_md.py
python3 tools/block_to_md.py rom.nes
python3 tools/block_to_md.py rom.nes --block 3
python3 tools/block_to_md.py rom.nes --block 4
python3 tools/block_to_md.py rom.nes --block 5
python3 tools/block_to_md.py rom.nes --block 6
python3 tools/sound_to_md.py rom.nes
python3 tools/demo_to_md.py rom.nes

# 5. Régénération des cartes de transition du château
python3 tools/record_maps.py
python3 tools/maps_to_md.py

# Compilation finale
make
```

---

## Description des scripts principaux

* **`tools/nes_dump.py`** : Éulateur NES headless (CPU via py65) utilisé par les scripts de capture.
* **`tools/block_to_md.py`** : Lit les pièces et blocs directement dans la ROM NES et convertit les ensembles CHR.
* **`tools/md_shot.py`** : Exécute une ROM construite dans un cœur libretro sans affichage pour effectuer des captures de contrôle.