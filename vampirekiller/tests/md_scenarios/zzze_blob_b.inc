# Salle courante en mode 16 bits : la flamme d'une bougie d'objet 15 brule en (120, 64) (fixture : enregistrement C500 0 en etat 1,
# contenu 15h, comme zzi_ghost4 le fait avec le fouet), 31 images plus tard elle s'eteint et l'objet 1B est cree en (X, Y + 16),
# puis attend (etat 0). Il est la goutte rouge 16 bits : contour noir (entree 2), corps rouge (entree 8), reflet blanc (entree 14),
# les trois lues dans PAL2 avec la meme couleur dans toutes les palettes de ces salles.
poke Enemies_god 1
until game.player.mode == 0 max 300
wait 20
set bg0 sorted({c for c in colors(112, 64, 128, 82)})
poke vk_candles+6 1
poke vk_candles+7 120
poke vk_candles+8 64
poke vk_candles+9 0
poke vk_candles+10 0
poke vk_candles+11 0
poke vk_candles+12 21
until any(enemies.enemy[k].active and enemies.enemy[k].type == 15 for k in range(7)) max 90
set bg [k for k in range(7) if enemies.enemy[k].active and enemies.enemy[k].type == 15][0]
expect (enemies.enemy[bg].x, enemies.enemy[bg].y, enemies.enemy[bg].state) == (120, 80, 0)
wait 2
set bc sorted({c for c in colors(112, 64, 128, 82)})
echo bc
expect (238, 0, 32) in bc and (238, 238, 238) in bc and (32, 32, 32) in bc # rouge, reflet blanc et noir
expect (238, 0, 32) not in bg0 # le rouge de l entree 8 n est pas dans le decor de la boite
