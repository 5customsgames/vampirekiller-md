# Journal des modifications (Changelog)

## Intermissions de la carte du château
* **Fonctionnalité :** Ajout des cartes de transition du château après les boss des stages 3, 6, 9, 12 et 15 (cartes vers les stages 4, 7, 10, 13 et 16).
* **Présentation :** Mode vidéo 256 pixels pendant la carte avec retour automatique au mode 320 pixels pour le jeu.
* **Reproduction :** Utilisation de `python3 tools/record_maps.py` et `python3 tools/maps_to_md.py` pour générer `src/maps.c` et `inc/maps.h`.
* **Tests :** Validé via `python3 tests/test_castle_maps.py`.

## Orchestration du prologue en FM/PSG
* **Fonctionnalité :** Réorchestration de la partition du prologue pour la Mega Drive sans échantillons MSU-1 (5 voix FM YM2612 et 1 voix PSG).
* **Taille :** 3 649 octets pour les données d'instruments et de séquence.
* **Outils :** `python3 tools/preparer_prologue_fm.py .` pour désactiver l'ancienne ressource PCM.
* **Tests :** Validé via `python3 tests/test_prologue_fm.py` et `python3 tools/build_fm_prologue.py .`.

## Cri de Wilhelm sur les chutes mortelles
* **Fonctionnalité :** Déclenchement du cri lors des chutes mortelles dans l'eau ou dans un trou quand la musique est réglée sur FM.
* **Ressources :** Fichier PCM 8-bit 22050 Hz (`res/audio/wilhelm.pcm`, ~34,25 Kio) chargé via SGDK DAC.
* **Tests :** Validé via `python3 tests/test_fatal_fall.py` et `python3 tests/test_soundtrack.py`.