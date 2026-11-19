# Castlevania MD (Final)

Portage Mega Drive / Genesis du jeu NES *Castlevania*, écrit en C avec [SGDK](https://github.com/Stephane-D/SGDK).
Il s'agit d'une réécriture complète et non d'une émulation : la logique du jeu est dans `src/main.c`, tandis que les graphismes et données de niveaux sont générés à partir d'une ROM NES.

---

## 🚀 Démarrage rapide

### Compilation
Depuis la racine du dépôt VampireCollectionNextGen (SGDK est dans `sgdk/`, voir le README de la racine) :
```bash
make cv
```
La ROM est copiée dans `out/castlevania-md.bin` à la racine ; `make` dans ce dossier marche aussi
(`castlevania/out/rom.bin`, après `make sgdk` à la racine).

---

## 🎮 État du projet

* **Progression :** Stages 1 à 18 intégrés (blocs 1 à 6) avec l'ensemble des ennemis, boss, objets, boucles de jeu et la séquence de fin.
* **Graphismes :** Modes 16-bit (assets SNES redessinés) et ORIGINAL (graphismes et palettes NES d'origine).
* **Audio :** Émulation de l'APU NES via PSG/FM, moteur FM dédié pour le prologue et gestion du DAC pour les bruitages PCM.
* **Debug & Options :** Écran d'options au démarrage, gestion de la difficulté, intermissions sur la carte du château et menu de triche/debug intégré.

---

## 📂 Documentation technique

La documentation détaillée a été répartie dans le dossier `docs/` pour faciliter la navigation :

1. 🛠️ **[Outils & Génération des données](docs/building-tools.md)** : Guide des scripts Python, extraction de la ROM NES et étapes de régénération.
2. 🎵 **[Moteur sonore & Musiques](docs/sound-engine.md)** : Architecture audio (FM, PSG, DAC), orchestration du prologue et gestion du cri de Wilhelm.
3. 🎨 **[Graphismes & Direction artistique](docs/graphics-art.md)** : Traitement des tuiles NES/SNES, palettes Mega Drive et décodage des cartes.

Consultez également le [CHANGELOG.md](CHANGELOG.md) pour suivre l'historique des évolutions récentes.
