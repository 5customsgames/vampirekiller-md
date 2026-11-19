# VampireCollectionNextGen: Castlevania-MD, Vampire Killer MD and the Vampire Collection (both in one
# 4 MiB ROM) from one tree, with its own SGDK. See README.md.
#
#   make              the three ROMs in out/
#   make cv           out/castlevania-md.bin
#   make vk           out/vampirekiller-md.bin
#   make collection   out/vampirecollection-md.bin
#   make sgdk         SGDK's libmd.a (and the host tools it needs), done by the targets above
#   make test         the tests of both games
#   make clean
#
# Needs on the host: m68k-elf-gcc (and binutils), a C/C++ compiler, Java, Python 3, rsync.
ROOT := $(CURDIR)
GDK := $(ROOT)/sgdk
PYTHON ?= python3
OBJCPY ?= m68k-elf-objcopy
HOST_BIN := $(ROOT)/build/host/bin
# sjasm and bintos (SGDK's Z80 drivers) are built from sgdk/tools: put them first in PATH.
export PATH := $(HOST_BIN):$(PATH)
LIBMD := $(GDK)/lib/libmd.a
# Extra -D flags for one game (test builds), e.g. make vk VK_FLAGS=-DGOD_MODE.
CV_FLAGS ?=
VK_FLAGS ?=

.PHONY: all cv vk collection sgdk host-tools test test-vk clean
.DEFAULT_GOAL := all
all: cv vk collection

# --- SGDK -------------------------------------------------------------------------------------------
host-tools: $(HOST_BIN)/sjasm $(HOST_BIN)/bintos
$(HOST_BIN)/sjasm: $(wildcard $(GDK)/tools/sjasm/src/*.cpp $(GDK)/tools/sjasm/src/*.h)
	@mkdir -p $(HOST_BIN)
	g++ -O2 -w -DMAX_PATH=MAXPATHLEN -include sys/param.h -o $@ $(GDK)/tools/sjasm/src/*.cpp
$(HOST_BIN)/bintos: $(GDK)/tools/bintos/src/bintos.c
	@mkdir -p $(HOST_BIN)
	gcc -O2 -w -o $@ $<

sgdk: $(LIBMD)
$(LIBMD): $(HOST_BIN)/sjasm $(HOST_BIN)/bintos $(GDK)/makelib.gen
	@mkdir -p $(GDK)/lib
	$(MAKE) -C $(GDK) -f makelib.gen release

# --- the games --------------------------------------------------------------------------------------
cv: $(LIBMD)
	$(MAKE) -C castlevania GDK=$(GDK) EXTRA_FLAGS="$(CV_FLAGS)" release
	@mkdir -p out
	cp castlevania/out/rom.bin out/castlevania-md.bin

vk: $(LIBMD)
	$(MAKE) -C vampirekiller/sgdk GDK=$(GDK) EXTRA_FLAGS="$(VK_FLAGS)"
	@mkdir -p out
	cp vampirekiller/sgdk/out/rom.bin out/vampirekiller-md.bin

collection: $(LIBMD)
	$(MAKE) -f collection/collection.mk ROOT=$(ROOT) GDK=$(GDK) PYTHON=$(PYTHON) OBJCPY=$(OBJCPY) \
		CV_FLAGS="$(CV_FLAGS)" VK_FLAGS="$(VK_FLAGS)"

# --- tests ------------------------------------------------------------------------------------------
# Vampire Killer's tests (README of vampirekiller/): native C tests, then the Python tests and the MD
# scenarios with the Python environment of .venv (make venv).
VENV := $(ROOT)/.venv
JOBS ?= $(shell nproc)
test: test-vk
test-vk: vk
	cd vampirekiller && PATH=$(VENV)/bin:$(PATH) sh tests/run_native.sh
	cd vampirekiller && $(VENV)/bin/python -m pytest -q -p no:cacheprovider tests
	@mkdir -p build/scenarios
	@cd vampirekiller && ls tests/md_scenarios/*.txt | xargs -P $(JOBS) -I{} sh -c \
		'n=$$(basename {} .txt); $(VENV)/bin/python tools/md_harness.py {} --out $(ROOT)/build/scenarios/$$n \
		--quiet > $(ROOT)/build/scenarios/$$n.log 2>&1 || echo "ECHEC $$n (build/scenarios/$$n.log)"' \
		| tee $(ROOT)/build/scenarios/failures.txt; \
		if [ -s $(ROOT)/build/scenarios/failures.txt ]; then exit 1; fi; \
		echo "scenarios MD : $$(ls tests/md_scenarios/*.txt | wc -l) OK"

.PHONY: venv
venv:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

clean:
	rm -rf build out castlevania/out vampirekiller/sgdk/out $(GDK)/out $(GDK)/lib/libmd.a
