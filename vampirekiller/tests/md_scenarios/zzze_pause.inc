# Pause, code Konami : le selecteur de stage de la pause est ouvert (suivent les DOWN du stage et le B qui le lance, ou les RIGHT de la salle).
until game.player.mode == 0 max 600
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
