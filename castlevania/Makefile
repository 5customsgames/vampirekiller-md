# Build with SGDK (see README.md for environment setup)
# The SGDK of this repository (../sgdk), built by the top Makefile.
GDK ?= $(abspath $(CURDIR)/../sgdk)
PYTHON ?= python3
export PATH := $(HOME)/.local/bin:$(PATH)
include $(GDK)/makefile.gen

# Run after SGDK has linked, padded and checksummed the selected build.
# This also applies when calling make release or make debug directly.
release debug:
	$(PYTHON) tools/pad_rom.py "$(OUT_DIR)/rom.bin"
	cp "$(OUT_DIR)/rom.bin" out/rom.bin
	cp "$(OUT_DIR)/rom.bin" out/Castlevania-md.bin

.DEFAULT_GOAL := castlevania
.PHONY: castlevania
castlevania: release
