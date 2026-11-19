# Route commune (zzze_gfx16_dracula.txt) : du titre a la salle 9 du stage 18 (stage 18, Dracula). Utilisee par zzzf_thanks_msx.txt et zzzf_thanks_16b.txt.
tap START
tap START
until front_mode == MODES['COURTYARD'] max 500
wait 60
tap START
until ram8('paused') == 1 max 30
tap UP
tap UP
tap DOWN
tap DOWN
tap LEFT
tap RIGHT
tap LEFT
tap RIGHT
tap B
tap A
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap DOWN
tap B
until game.stage == 18 and game.room == 0 max 300
poke Enemies_god 1
poke vk_enemies+162 1
until game.player.mode == 0 max 300
poke vk_game+16 1 32
poke vk_game+22 18
poke vk_game+20 8
poke vk_front_mode 4 16
poke vk_game+0 24
poke vk_game+1 120
poke vk_game+2 0
poke vk_game+3 0
poke vk_game+4 0
poke vk_game+7 0
poke vk_game+8 0
poke vk_game+23 0
poke vk_game+26 0
poke vk_game+30 0
poke vk_candles 255
poke health+1 0
poke health+2 0 16
poke Enemies_god 1
poke vk_enemies+162 1
poke items+2 0
poke items+3 0
poke freeze_drawn 0
poke room_freeze 4
poke room_freeze+1 4
poke room_freeze+2 0
write freeze_vtimer 32 ram32('vtimer')
until ram8('room_freeze') == 0 and ram8('freeze_drawn') != 0 max 100
wait 30
poke items 1
poke vk_game+2 1
poke vk_game+0 20
poke vk_game+1 144
poke vk_game+3 0
until ram8('items+2') == 1 max 60 LEFT
until game.room == 9 max 500
wait 60
