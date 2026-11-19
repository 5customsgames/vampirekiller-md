include zzp_dracula_hit2.inc
when any(ram8('dracula+%d' % (32 * k)) in (12, 30) for k in range(15)) and len(linked_sprites(760, 855)) > 0 :: set fl sorted({c for s in linked_sprites(760, 855) for c in colors(s[1], s[2], s[1] + 16, s[2] + 16)})
when any(ram8('dracula+%d' % (32 * k)) in (12, 30) for k in range(15)) and len(linked_sprites(760, 855)) > 0 :: shot zzze-dracula-flammes
