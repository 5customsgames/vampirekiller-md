# Un echantillon par image de l'aigle (type 18, stage 17) : pixels couleur d'aigle (entrees libres 5 et 4) dans le coin haut gauche
# 8 x 8 de sa toile 32 x 32 (X - 16, Y - 30) : la colonne gauche (seconde aile) ne l'a qu'aux poses ailes levees.
set ex [enemies.objects[k].x for k in range(15) if enemies.objects[k].active and enemies.objects[k].type == 18][0]
set ey [enemies.objects[k].y for k in range(15) if enemies.objects[k].active and enemies.objects[k].type == 18][0]
set tls tls + [len([c for c in colors(ex - 16, ey - 30, ex - 8, ey - 22) if c in ((65, 68, 98), (65, 0, 0))])]
wait 1
