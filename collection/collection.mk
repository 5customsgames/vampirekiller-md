# Vampire Collection MD: Castlevania-MD and Vampire Killer MD in one 4 MiB ROM, no mapper (README.md).
# Run by the top Makefile (make collection). Both games are mirrored into build/collection and built
# there as two separate SGDK programs: Castlevania linked at 0 (it owns the 68000 vectors and the
# boot screens), Vampire Killer linked alone at VK_BASE; collection/merge_rom.py appends one to the other.
ROOT ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
GDK ?= $(ROOT)/sgdk
PYTHON ?= python3
OBJCPY ?= m68k-elf-objcopy
# Extra -D flags for each game's build in the collection.
CV_FLAGS ?=
VK_FLAGS ?=

# Where Vampire Killer starts: past Castlevania-MD's code and data (0x211C04 bytes), on a 16 KiB boundary.
# merge_rom.py stops if Castlevania grows past it, or Vampire Killer past 4 MiB.
VK_BASE := 0x214000

COLL_SRC := $(ROOT)/collection
COLL := $(ROOT)/build/collection
CV_STAGE := $(COLL)/cv
VK_STAGE := $(COLL)/vk
ROM := $(ROOT)/out/vampirecollection-md.bin

# SGDK's makefile.gen with the linker script and boot file given by LINKER_SCRIPT and SEGA_S, and the
# two linker scripts. A file is rewritten only when its text changes, so make sees no needless update.
define write_if_changed
$(shell mkdir -p $(COLL); $(1) > $(2).tmp && { cmp -s $(2).tmp $(2) && rm $(2).tmp || mv $(2).tmp $(2); })
endef
$(call write_if_changed,sed -e '/Cannot find SGDK environment/d' -e 's|-T $$(GDK)/md.ld|-T $$(LINKER_SCRIPT)|' -e 's|$$(SRC_LIB)/boot/sega.s|$$(SEGA_S)|' $(GDK)/makefile.gen,$(COLL)/makefile.gen)
$(call write_if_changed,sed -e 's|TEXT_BASE|0x00000000|' -e 's|GAME_FLAG_VALUE|0|' $(COLL_SRC)/md_collection.ld.in,$(COLL)/cv.ld)
$(call write_if_changed,sed -e 's|TEXT_BASE|$(VK_BASE)|' -e 's|GAME_FLAG_VALUE|$(VK_BASE)|' $(COLL_SRC)/md_collection.ld.in,$(COLL)/vk.ld)
$(call write_if_changed,echo $(VK_BASE),$(COLL)/vk_base)

.PHONY: collection cv vk
.DEFAULT_GOAL := collection

cv:
	@mkdir -p $(CV_STAGE)
	rsync -a --delete $(ROOT)/castlevania/src/ $(CV_STAGE)/src/
	rsync -a --delete $(ROOT)/castlevania/res/ $(CV_STAGE)/res/
	rsync -a --delete $(ROOT)/castlevania/inc/ $(CV_STAGE)/inc/
	rsync -a $(COLL_SRC)/cv/ $(CV_STAGE)/
	$(MAKE) -C $(CV_STAGE) -f $(COLL_SRC)/cv.mk GDK=$(GDK) COLL=$(COLL) COLL_SRC=$(COLL_SRC) \
		VK_BASE=$(VK_BASE) EXTRA_FLAGS="$(CV_FLAGS)" release

vk:
	@mkdir -p $(VK_STAGE)
	rsync -a --delete $(ROOT)/vampirekiller/sgdk/src/ $(VK_STAGE)/src/
	rsync -a --delete $(ROOT)/vampirekiller/sgdk/res/ $(VK_STAGE)/res/
	$(MAKE) -C $(VK_STAGE) -f $(COLL_SRC)/vk.mk GDK=$(GDK) COLL=$(COLL) EXTRA_FLAGS="$(VK_FLAGS)" release

# Both images straight from their ELF: SGDK pads its rom.bin (sizebnd, 128 KiB multiple).
collection: cv vk
	@mkdir -p $(dir $(ROM))
	$(OBJCPY) -O binary $(CV_STAGE)/out/release/rom.out $(COLL)/castlevania.bin
	$(OBJCPY) -O binary $(VK_STAGE)/out/release/rom.out $(COLL)/vampirekiller.bin
	$(PYTHON) $(COLL_SRC)/merge_rom.py --vk-base $(VK_BASE) $(COLL)/castlevania.bin $(COLL)/vampirekiller.bin $(ROM)
