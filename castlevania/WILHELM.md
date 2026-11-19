# Cri de Wilhelm sur les chutes mortelles, en mode FM

Simon déclenche désormais le cri de Wilhelm lorsqu’une chute dans l’eau ou
dans un trou provoque sa mort. Le déclenchement se fait au seuil de chute
mortelle existant, une fois par décès. Une nouvelle chute après le redémarrage
peut déclencher un nouveau cri.

Le cri est actif uniquement lorsque MUSIC est réglé sur FM. Le mode ORIGINAL,
les dégâts ordinaires, les morts par ennemi ou par expiration du temps ne
changent pas. Les entrées de niveau animées par ST_CLIMB restent exclues du
contrôle de chute, comme auparavant.

## Installation

Appliquer sur le projet avec la mise à jour
`Castlevania-MD-bande-son-FM-menu.zip` déjà installée.

Extraire les fichiers à la racine du projet, puis compiler normalement avec
SGDK. Les fichiers existants remplacés sont :

- `src/main.c` : un seul appel au bruitage est ajouté au passage à la mort
  par chute ; le menu musical et les correctifs précédents sont conservés.
- `src/sound.c` et `inc/sound.h` : ajout de l’API `fall_play`, conditionnée au
  choix FM.
- `tests/test_soundtrack.py` : le test audio prend en compte la nouvelle
  ressource et vérifie aussi la cohabitation avec le jingle de mort.

Les nouveaux fichiers `res/wilhelm_audio.res`, `res/wilhelm_audio.h` et
`res/audio/wilhelm.pcm` fournissent le sample. Le Makefile SGDK existant prend
automatiquement en charge la ressource `.res`.

La musique reste en FM/PSG. Seul le cri est un court enregistrement PCM lu par
le DAC déjà réservé aux effets sonores. Il peut remplacer le bruit bref de
Simon blessé si une chute mortelle survient pendant ce bruit. Le jingle de
mort utilise les autres canaux et ne coupe pas le cri.

## Taille et écoute

Format : mono, 8 bits signés, 22 050 Hz, sans boucle, avec de courts fondus.
La durée est d’environ 1,59 seconde, silence d’alignement compris, donc inférieure
aux 97 frames de mort à 60 Hz. La ressource ajoute **35 072 octets**, soit
**34,25 Kio**, hors quelques instructions de code.

`res/audio/wilhelm-preview.wav` est un aperçu du sample réellement converti.
Il n’est pas ajouté à la ROM ; seul le PCM brut est compilé. Les empreintes et
le format sont enregistrés dans `res/audio/wilhelm.json`.

## Vérifications

```sh
python3 tests/test_fatal_fall.py
python3 tests/test_soundtrack.py
```

Le test de chute compile le véritable contrôle de mort et la fonction de lecture.
Il vérifie le seuil, les deux modes, le déclenchement unique, une seconde chute,
les états déjà morts et les entrées de niveau. Le format PCM, l’alignement,
l’empreinte et la durée sont également contrôlés.

Le test audio compile le moteur sonore et le lecteur FM : il vérifie que le
jingle de mort laisse le DAC jouer le cri et que le mode Original ne le déclenche
pas. Les traces des 15 musiques, leurs boucles et les 38 bruitages existants
continuent de passer les tests locaux.

Aucune ROM complète n’a été compilée ni testée sur Mega Drive ou émulateur
complet pour cette mise à jour.

## Source du cri

Fichier : Wilhelm Scream.ogg, version actuelle datée du 22 mai 2023 sur Commons,
extrait par Ruxnor de la bibliothèque Sunset Editorial conservée par USC.
La page indique la dédicace CC0 1.0 ; l’interprète est attribué avec réserve à
Sheb Wooley.

https://commons.wikimedia.org/wiki/File:Wilhelm_Scream.ogg
https://creativecommons.org/publicdomain/zero/1.0/

La conversion peut être reproduite avec FFmpeg :

```sh
python3 tools/convert_wilhelm.py /chemin/Wilhelm_Scream.ogg
```
