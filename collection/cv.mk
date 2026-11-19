# Castlevania-MD inside the collection: run by collection.mk from build/collection/cv, a mirror of
# castlevania/src, res and inc with the files of collection/cv laid over them (collection.c/.h: the
# launch of Vampire Killer; src/rom_header.c: the collection's header). Linked at 0 by $(COLL)/cv.ld,
# with the relay vectors of collection/sega_cv.s as boot file; VK_BASE turns on the SELECT GAME screen.
ifndef GDK
$(error GDK manquant)
endif
ifndef COLL
$(error COLL manquant : lancer depuis le Makefile de la racine)
endif
ifndef VK_BASE
$(error VK_BASE manquant)
endif

LINKER_SCRIPT := $(COLL)/cv.ld
SEGA_S := $(COLL_SRC)/sega_cv.s
# override: still added when EXTRA_FLAGS is given on the command line (test builds).
override EXTRA_FLAGS += -DVK_BASE=$(VK_BASE)
include $(COLL)/makefile.gen

# The objects that use VK_BASE are rebuilt when it changes (make does not track the -D flags).
$(OUT_DIR)/sega.o: $(SEGA_S) $(COLL)/vk_base
$(OUT_DIR)/src/collection.o: $(COLL)/vk_base
$(OUT_DIR)/rom.out: $(LINKER_SCRIPT)
