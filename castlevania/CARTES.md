# Ajout des scènes de carte

Décompresser ce ZIP à la racine du projet, en conservant les dossiers src/, inc/,
tools/ et tests/. Puis recompiler normalement avec l'environnement SGDK existant.
Les données C sont déjà générées : aucun nouvel outil n'est requis pour compiler.

Les sources main.c fournies conservent tous les correctifs précédents :
atterrissage de Simon, dégâts dans les démos, collisions latérales des sauteurs,
sons des éclaboussures et synchronisation des portes. Le correctif du moteur
audio déjà fourni dans src/sound.c et les données du titre src/screens.c doivent
également rester dans le projet ; ces fichiers n'ont pas été modifiés ici.

## Scènes ajoutées

- Après le boss du stage 3 : carte vers le stage 4, 397 frames.
- Après le boss du stage 6 : carte vers le stage 7, 397 frames.
- Après le boss du stage 9 : carte vers le stage 10, 482 frames.
- Après le boss du stage 12 : carte vers le stage 13, 482 frames.
- Après le boss du stage 15 : carte vers le stage 16, 482 frames.

Le défilement, les poses de Simon, les repères clignotants et les sons de pas
sont enregistrés depuis le code NES conservé par le port SNES. Les graphismes
16 bits utilisent sa palette 09. Le HUD est fixe et affiche les valeurs réelles
de la partie, y compris l'arme conservée. Le compteur de temps et le gameplay
ne continuent pas à tourner pendant cette séquence.

La présentation emploie le mode vidéo 256 pixels de large pendant la carte,
puis revient en 320 pixels pour le jeu, avec rechargement des plans, du HUD,
des tiles et de la palette. Les passages de portes ordinaires n'ajoutent pas de
carte. Une mort ne déclenche pas de carte. Dracula conserve sa scène de fin.

## Origine et reproduction

Référence : https://github.com/rumbleminze/castlevania-snes
Commit consulté : f7490c28fd58aa59f4b2cb5d3077cb2f24939b7b
Séquence : src/bank7.asm, adresses NES $C698-$C7E2.
Palette : src/palette_updates.asm, system_state_palettes, état $0C -> palette $09.

Les ressources tools/extracted/maps sont fournies pour la reproductibilité.
Pour les refaire avec les données PRG et SNES déjà extraites du projet :

    python3 tools/record_maps.py
    python3 tools/maps_to_md.py

Le premier script nécessite py65, comme les autres scripts d'enregistrement.
Le convertisseur screens_to_md.py accepte désormais des tiles et sprites
supplémentaires ; ses sorties existantes (titre, introduction, fin) ont été
régénérées et vérifiées identiques aux versions précédentes.

## Vérifications

- Les cinq séquences sont testées en modes NES et 16 bits avec chacune des cinq
  armes secondaires, ainsi que sans arme.
- Le défilement circulaire des colonnes est vérifié sur toutes les frames,
  notamment après le rebouclage au-delà de 512 pixels.
- Les tests vérifient les sons de pas, le HUD fixe avec les valeurs courantes,
  la restauration du mode 320, les transitions après boss, la conservation des
  armes/niveaux de tirs et le maintien de la fin de Dracula.
- Les pixels NES des 163 combinaisons de tiles de fond/sprites sont identiques
  aux données sources. Les palettes 16 bits sont adaptées aux quatre palettes
  Mega Drive ; quelques couleurs proches sont fusionnées.
- Vérification syntaxique C avec les en-têtes SGDK effectuée.
- Aperçu reconstruit : apercu-cartes.png (exemple de score 123450).

L'installation de SGDK a été arrêtée à ta demande. Cette livraison contient
les sources et les données à compiler, pas une ROM recompilée. Le test de
l'ensemble dans un émulateur Mega Drive reste à faire.
