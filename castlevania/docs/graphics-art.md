# Graphismes et Gestion de l'Art

La Mega Drive dispose de 4 palettes de 16 couleurs, ce qui impose une stratégie de conversion pour adapter les assets NES et SNES.

---

## 1. Modes graphiques

Le menu des options permet de basculer instantanément entre deux rendus :

* **16-BIT (SNES) :** Tuiles redessinées issues du projet SNES de Rumbleminze.
* **ORIGINAL (NES) :** Graphismes NES d'origine adaptés avec support des 14 palettes NES sélectionnables dans le menu (FCEUX, Real, Smooth, Greyscale, Virtual Boy, etc.).

---

## 2. Allocation des palettes Mega Drive

Afin de maximiser le rendu avec seulement 4 palettes de 16 couleurs (contre 8 sur SNES) :

1. **Arrière-plan (2 palettes) :** `block_to_md.py` évalue chaque tuile de fond et lui attribue la palette qui offre la meilleure fidélité parmi les graphismes NES et 16-bit.
2. **Sprites (2 palettes) :** Les sprites fixes (Simon, HUD) conservent leurs palettes dédiées, tandis que les ennemis sont répartis dynamiquement dans les palettes disponibles.

---

## 3. Cartes de transition du château (`CARTES.md`)

Les intermissions affichées après les boss des stages 3, 6, 9, 12 et 15 basculent l'affichage :

* **Résolution :** Utilisation du mode 256 pixels de large pendant la carte.
* **Transition :** Bascule automatique en mode 320 pixels pour le gameplay avec rechargement des plans, du HUD et des palettes.
* **HUD :** Reste fixe et affiche le score et l'équipement réels du joueur sans faire défiler le timer.