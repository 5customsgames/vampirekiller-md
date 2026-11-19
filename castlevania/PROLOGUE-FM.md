# Première orchestration du prologue en FM/PSG

Cette version reprend la partition du prologue original déjà présente dans
`src/music.c` et la réorchestre pour la Mega Drive. Elle n’utilise aucun
échantillon du pack MSU-1 et ne cherche pas à copier son enregistrement orchestral.

Cinq voix FM du YM2612 sont utilisées : mélodie de type cuivre, accompagnement
orgue, basse et deux doublures plus discrètes de type cloche et nappe. Une voix
PSG apporte une touche aiguë. Le sixième canal FM reste réservé au DAC pour les
bruitages PCM du jeu après l’introduction.

## Écouter

- `apercu/Prologue-FM-PSG.vgm` : commandes réelles YM2612/PSG, pour lecteur VGM.

L’aperçu a été rendu par l’émulateur de puces de libgme via FFmpeg. Le test
compare chaque écriture YM2612 du lecteur C à celles de ce VGM. Il ne s’agit
pas d’une capture de la ROM dans un émulateur Mega Drive complet.

## Installation

Copier `src`, `inc` et `tools` dans le projet corrigé. Le seul fichier existant
remplacé est `src/sound.c`, basé sur celui de l’archive `castlevania-md_2.zip`
avec les enveloppes et les précédentes corrections audio. Les fichiers de
collisions, de boss et de carte ne sont pas modifiés.

Si le prologue PCM précédent a été installé, exécuter :

```sh
python3 tools/preparer_prologue_fm.py .
```

Cette commande désactive uniquement sa ressource `.res`, en la conservant sous
un autre nom. Cela évite de garder les 239 Kio de cet ancien enregistrement dans
la compilation. Si le PCM n’a pas été installé, elle ne change rien.

Compiler ensuite avec l’installation SGDK habituelle. `main.c` continue d’appeler
`music_play(MUS_PROLOGUE)` ; cet appel choisit maintenant le lecteur FM/PSG.
À la fin ou lors du passage au niveau, les voix utilisées sont arrêtées, la voix
triangle habituelle est restaurée, les caches sonores sont réinitialisés et
les musiques et bruitages du jeu reprennent leur fonctionnement existant.

Aucune ressource audio de `apercu/` n’est incluse dans la ROM.

## Taille et durée

Les données des instruments et de la séquence occupent **3 649 octets**, auxquels
s’ajoute le code du petit lecteur. C’est la taille des données, pas une mesure
d’une ROM finale recompilée. L’ancien enregistrement NES reste dans la table
du projet ; son retrait n’est pas nécessaire à ce premier essai.

La séquence dure 458 frames : 7,63 secondes à 60 Hz. Sur une console PAL à
50 Hz, elle suit le rythme de la scène, soit 9,16 secondes, tout en conservant
les hauteurs des notes. Les instruments sont des synthèses FM : il n’y a aucun
échantillon enregistré dans les nouvelles données musicales.

## Vérifications

```sh
python3 tests/test_prologue_fm.py
python3 tools/build_fm_prologue.py .
```

La première commande teste le lecteur et le moteur sonore. La seconde régénère
les données FM et le VGM à partir du prologue NES et des paramètres d’instruments
présents dans l’outil ; elle nécessite un compilateur C natif accessible par `cc`.
La compilation habituelle SGDK utilise directement les données fournies et
n’exige pas cette régénération.

475 contrôles locaux passent. Les 898 écritures YM2612 correspondent au VGM de
l’aperçu ; le fichier comprend également 248 écritures PSG. Les tests couvrent
les 458 frames, les interruptions, les données tronquées, l’absence de données
DAC, la reprise de la musique et du bruitage d’impact, et le bruit PCM de Simon.

Le rendu WAV ne présente aucun échantillon écrêté. La ROM complète n’a pas été
compilée et le résultat n’a pas encore été validé sur console ou émulateur
Mega Drive complet. L’installation de SGDK n’a pas été reprise.

Référence du format de l’aperçu :
https://github.com/vgmrips/vgmplay-legacy/blob/master/VGMPlay/vgmspec171.txt
