# Vampire Killer MD inside the collection: run by collection.mk from build/collection/vk (a mirror of
# vampirekiller/sgdk/src and res). Same sources and flags as vampirekiller/sgdk/Makefile,
# but linked at VK_BASE by $(COLL)/vk.ld. The SGDK boot file and header stay: Castlevania's relay
# vectors read this build's vector table at VK_BASE, and its entry point clears the RAM as usual.
ifndef GDK
$(error GDK manquant)
endif
ifndef COLL
$(error COLL manquant : lancer depuis le Makefile de la racine)
endif

# See vampirekiller/sgdk/Makefile: GCC 15+ late-combine makes odd-address word loads.
NO_LATE_COMBINE = $(shell echo | $(CC) -fno-late-combine-instructions -x c -E - >/dev/null 2>&1 && echo -fno-late-combine-instructions)
override EXTRA_FLAGS += -std=c99 $(NO_LATE_COMBINE)

LINKER_SCRIPT := $(COLL)/vk.ld
SEGA_S = $(SRC_LIB)/boot/sega.s
include $(COLL)/makefile.gen

SRC_S := $(filter-out src/boot/sega.s,$(SRC_S))
SRC_C := $(filter-out src/boot/rom_head.c src/rom_header.c,$(SRC_C))
OBJS := $(filter-out $(OUT_DIR)/src/boot/sega.o $(OUT_DIR)/src/boot/rom_head.o $(OUT_DIR)/src/rom_header.o,$(OBJS))

$(OUT_DIR)/rom.out: $(LINKER_SCRIPT)
