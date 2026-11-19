# Moteur sonore et Audio

L'architecture audio de Castlevania MD combine le processeur YM2612 (FM + DAC) et la puce SN76489 (PSG).

---

## 1. Émulation APU NES (`src/sound.c`)

Le script `tools/sound_to_md.py` simule le moteur sonore NES d'origine (Banque 0) et enregistre les écritures APU trame par trame pour les 15 pistes et les effets sonores.

* **Canaux PSG :** Reproduisent les deux voies Pulse de la NES (duty cycle fixe à 50%) ainsi que le canal Bruit (Noise).
* **Canal FM :** Reproduit la voie Triangle sous la forme d'une onde sinusoïdale FM à un opérateur.
* **Canal DAC (FM6) :** Utilisé pour la lecture PCM 8-bit (impacts de Simon, cri de Wilhelm).

---

## 2. Orchestration FM du Prologue (`PROLOGUE-FM.md`)

Une réorchestration dédiée du prologue est disponible sans recours aux échantillons MSU-1 :

* **Voies utilisées :** 5 canaux FM (mélodie cuivre, orgue, basse, cloche, nappe) et 1 canal PSG (aigu).
* **DAC :** Le 6e canal FM reste libre pour les effets sonores PCM du jeu.
* **Aperçus :** Des fichiers de contrôle sont disponibles dans `apercu/Prologue-FM-PSG.vgm`.

### Activation / Bascule
Pour désactiver la ressource PCM précédente et utiliser l'orchestration FM :
```bash
python3 tools/preparer_prologue_fm.py .
```

---

## 3. Effet PCM : Cri de Wilhelm (`WILHELM.md`)

Simon déclenche le cri de Wilhelm lors d'une chute mortelle dans un trou ou dans l'eau.

* **Conditions :** Uniquement actif si la musique est réglée sur le mode FM.
* **Format :** PCM 8-bit signé mono à 22050 Hz (`res/audio/wilhelm.pcm`), occupant environ 34 Kio.
* **Priorité :** Mis en œuvre sur le DAC dédié sans couper le jingle de mort joué sur les autres canaux.