/* Included first by the files that are compiled with -O2 instead of the -O3 of SGDK's makefile.gen (research/rom-budget.md 7.3):
 * -O3 inlines every static function that has several callers and unrolls loops, which costs code (enemies.c: 84 Kio -> 57 Kio)
 * where the speed does not matter (menus, maps, scenes) or where the 12-18 replay shows that no slack is lost.
 * The options of the makefile that the pragma would reset are repeated. */
#ifdef SGDK_GCC   /* not in the native tests */
#pragma GCC optimize("O2,no-ivopts,no-store-merging,no-web,no-gcse,no-tree-loop-ivcanon,omit-frame-pointer")
#endif
